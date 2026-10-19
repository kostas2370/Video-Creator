from django.db import models
from django.db.models import Count, Min, Q, Sum

from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.videomanagement.services.voices.credentials import key_fingerprint, key_source

from . import models as video_models

TOKEN_METRICS = {
    "input_tokens": "requests_with_input_tokens",
    "output_tokens": "requests_with_output_tokens",
    "total_tokens": "requests_with_tokens",
}


class AIUsageQuerySet(models.QuerySet):
    def first_recorded_at(self):
        return self.aggregate(first=Min("created_at"))["first"]

    def summary(self):
        """Aggregate this selection, preserving unknown and partially reported counts."""
        # Count availability before sum aliases shadow their source fields.
        metrics = {
            coverage: Count("id", filter=Q(**{f"{field}__isnull": False}))
            for field, coverage in TOKEN_METRICS.items()
        }
        metrics["requests"] = Count("id")
        metrics.update(
            {
                field: Sum(field, default=0)
                for field in (*TOKEN_METRICS, "characters", "images", "seconds")
            }
        )

        def preserve_unknowns(row):
            for field, coverage in TOKEN_METRICS.items():
                if row["requests"] and not row[coverage]:
                    row[field] = None
            return row

        grouping = ("service", "provider", "model", "key_source")
        return {
            "totals": preserve_unknowns(self.aggregate(**metrics)),
            "breakdown": [
                preserve_unknowns(row)
                for row in self.values(*grouping)
                .annotate(**metrics)
                .order_by(*grouping)
            ],
        }


class VideoQuerySet(models.QuerySet):
    def for_user(self, user):
        if user is None or not user.is_authenticated:
            return self.none()
        return self.filter(created_by=user)

    def listable(self):
        """Manual projects and AI projects with a generated script."""
        return self.filter(
            Q(gpt_answer__isnull=False) | Q(video_type=video_models.VideoType.MANUAL)
        )

    def in_flight(self):
        return self.filter(status__in=video_models.IN_FLIGHT_STATUSES)


class SceneQuerySet(models.QuerySet):
    def with_media(self):
        """Load scene visuals in one extra query, retaining existing ordering."""
        return self.prefetch_related("scene_images")


class VoiceModelQuerySet(models.QuerySet):
    def available_to(self, user):
        """Shared/account voices plus ready clones created with the active key."""
        if user is not None and not user.is_authenticated:
            return self.none()

        playable = [
            provider
            for provider in video_models.VOICE_PROVIDERS
            if ApiKeys.key_for(user, provider)
        ]
        valid_providers = Q(provider__in=playable) | Q(
            type=video_models.VoiceModelType.CUSTOM_API,
            created_by=user,
        )
        voices = self.filter(is_cloned=False, created_by=None)
        if user is None:
            return voices.filter(valid_providers)

        if not user.use_service_api_keys:
            voices = voices.exclude(
                provider__in=video_models.ACCOUNT_SCOPED_VOICE_PROVIDERS
            )
            voices |= self.filter(is_cloned=False, created_by=user)

        clones = self.filter(
            is_cloned=True,
            created_by=user,
            requires_verification=False,
            clone_key_source=key_source(user),
            clone_key_fingerprint=key_fingerprint(
                ApiKeys.key_for(user, Provider.ELEVENLABS)
            ),
        )
        return (voices | clones).filter(valid_providers)
