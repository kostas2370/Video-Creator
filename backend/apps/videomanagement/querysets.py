from django.db import models
from django.db.models import Prefetch, Q

from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.videomanagement.services.voices.credentials import key_fingerprint, key_source

from . import models as video_models


class VideoQuerySet(models.QuerySet):
    def with_editor_media(self):
        """Load scene visuals and their assets together instead of a query per relation."""
        return self.select_related("music", "prompt", "intro", "outro").prefetch_related(
            Prefetch("scenes", queryset=video_models.Scene.objects.with_media())
        )

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
        return self.select_related("starting_asset").prefetch_related(
            Prefetch(
                "scene_images",
                queryset=video_models.SceneImage.objects.select_related("asset"),
            )
        )


class ActiveSceneManager(models.Manager.from_queryset(SceneQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(archived_at__isnull=True)


class VoiceModelQuerySet(models.QuerySet):
    def available_to(self, user):
        """Shared/account voices plus ready clones created with the active key."""
        if user is not None and not user.is_authenticated:
            return self.none()

        keys = ApiKeys.keys_for(user, video_models.VOICE_PROVIDERS)
        playable = [
            provider
            for provider in video_models.VOICE_PROVIDERS
            if keys[provider]
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
            clone_key_fingerprint=key_fingerprint(keys[Provider.ELEVENLABS]),
        )
        return (voices | clones).filter(valid_providers)
