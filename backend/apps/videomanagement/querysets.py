from django.db import models
from django.db.models import Count, Min, Q, Sum


class AIUsageQuerySet(models.QuerySet):
    def first_recorded_at(self):
        return self.aggregate(first=Min("created_at"))["first"]

    def summary(self):
        """Aggregate only this queryset's records into totals and grouped rows."""
        metrics = {
            # Resolve this filter before the total_tokens aggregation shadows the field.
            "requests_with_tokens": Count("id", filter=Q(total_tokens__isnull=False)),
            "requests": Count("id"),
            "input_tokens": Sum("input_tokens", default=0),
            "output_tokens": Sum("output_tokens", default=0),
            "total_tokens": Sum("total_tokens", default=0),
            "characters": Sum("characters", default=0),
            "images": Sum("images", default=0),
            "seconds": Sum("seconds", default=0),
        }
        grouping = ("service", "provider", "model", "key_source")
        return {
            "totals": self.aggregate(**metrics),
            "breakdown": list(
                self.values(*grouping).annotate(**metrics).order_by(*grouping)
            ),
        }


class VideoQuerySet(models.QuerySet):
    def for_user(self, user):
        if not getattr(user, "is_authenticated", False):
            return self.none()
        return self.filter(created_by=user)

    def listable(self):
        """Manual projects and AI projects with a generated script."""
        from .models import VideoType

        return self.filter(Q(gpt_answer__isnull=False) | Q(video_type=VideoType.MANUAL))

    def in_flight(self):
        from .models import IN_FLIGHT_STATUSES

        return self.filter(status__in=IN_FLIGHT_STATUSES)


class SceneQuerySet(models.QuerySet):
    def with_media(self):
        """Load scene visuals in one extra query, retaining existing ordering."""
        return self.prefetch_related("scene_images")


class VoiceModelQuerySet(models.QuerySet):
    def available_to(self, user):
        from apps.apikeysmanagement.models import ApiKeys
        from .models import (
            VOICE_PROVIDERS,
            ACCOUNT_SCOPED_VOICE_PROVIDERS,
            VoiceModelType,
        )

        playable = [
            provider for provider in VOICE_PROVIDERS if ApiKeys.key_for(user, provider)
        ]
        spending_own_keys = (
            user is not None
            and getattr(user, "is_authenticated", False)
            and not user.use_service_api_keys
        )
        shared = models.Q(created_by=None)
        if spending_own_keys:
            scope = (
                shared & ~models.Q(provider__in=ACCOUNT_SCOPED_VOICE_PROVIDERS)
            ) | models.Q(created_by=user)
        else:
            scope = shared

        valid_providers = models.Q(provider__in=playable) | (
            models.Q(type=VoiceModelType.CUSTOM_API) & models.Q(created_by=user)
        )

        return self.filter(scope & valid_providers)
