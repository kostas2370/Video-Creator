from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.functional import cached_property

from apps.common.models import TimestampedModel, UUIDModel
from apps.videomanagement.models import (
    AbstractModel,
    Intro,
    Outro,
    Video,
    VideoStatus,
    VoiceModel,
)
from apps.videomanagement.video_formats import (
    VIDEO_FORMAT_CHOICES,
    VIDEO_PLATFORM_CHOICES,
)

from .memory import video_script_snapshot
from .querysets import SeriesEpisodeQuerySet


CHARACTER_IDENTITY_FIELDS = ("name", "appearance", "wardrobe")
CHARACTER_PROFILE_FIELDS = (*CHARACTER_IDENTITY_FIELDS, "personality", "relationships")
CHARACTER_REFERENCE_FIELDS = (*CHARACTER_IDENTITY_FIELDS, "visual_style")


class CharacterIdentityFields(models.Model):
    name = models.CharField(max_length=60)
    appearance = models.CharField(max_length=300)
    wardrobe = models.CharField(max_length=150, blank=True, default="")

    class Meta:
        abstract = True


class CharacterReference(CharacterIdentityFields, AbstractModel, TimestampedModel):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        GENERATING = "GENERATING", "Generating"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    image = models.ImageField(upload_to="media/characters/%Y/%m/%d", blank=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.QUEUED
    )
    visual_style = models.TextField(max_length=800, blank=True, default="")
    error = models.CharField(max_length=300, blank=True)

    def generation_brief(self):
        """The fixed identity/style that this particular image was requested with."""
        return {field: getattr(self, field) for field in CHARACTER_REFERENCE_FIELDS}


class VideoSeries(AbstractModel, TimestampedModel):
    title = models.CharField(max_length=100)
    premise = models.TextField(max_length=2000)
    characters = models.TextField(max_length=2000, blank=True)
    story_format = models.CharField(
        max_length=20,
        choices=[
            ("GENERAL", "General series"),
            ("ANIMATED_STORY", "Animated character story"),
            ("SERIAL_DRAMA", "Serial drama"),
        ],
        default="GENERAL",
    )
    visual_style = models.TextField(max_length=800)
    reference_image = models.ImageField(upload_to="media/series/%Y/%m/%d", blank=True)
    voice_model = models.ForeignKey(
        VoiceModel, null=True, blank=True, on_delete=models.SET_NULL
    )
    intro = models.ForeignKey(Intro, null=True, blank=True, on_delete=models.SET_NULL)
    outro = models.ForeignKey(Outro, null=True, blank=True, on_delete=models.SET_NULL)
    provider = models.CharField(max_length=100, default="OPENAI")
    narration = models.BooleanField(default=True)
    subtitles = models.BooleanField(default=True)
    video_format = models.CharField(
        max_length=12, choices=VIDEO_FORMAT_CHOICES, default="PORTRAIT"
    )
    platform = models.CharField(
        max_length=12, choices=VIDEO_PLATFORM_CHOICES, default="GENERAL"
    )
    scene_count = models.PositiveSmallIntegerField(
        default=6, validators=[MinValueValidator(1), MaxValueValidator(60)]
    )

    @property
    def cast(self):
        """Keep the public ordered cast representation separate from relational storage."""
        return [character.as_cast_entry() for character in self.character_profiles.all()]

    class Meta:
        db_table = "videomanagement_videoseries"
        ordering = ["-updated_at", "id"]


class SeriesCharacter(CharacterIdentityFields, UUIDModel, TimestampedModel):
    series = models.ForeignKey(
        VideoSeries, on_delete=models.CASCADE, related_name="character_profiles"
    )
    character_id = models.UUIDField()
    position = models.PositiveSmallIntegerField()
    personality = models.CharField(max_length=200, blank=True, default="")
    relationships = models.CharField(max_length=200, blank=True, default="")
    reference = models.ForeignKey(
        CharacterReference, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="character_profiles",
    )
    reference_job = models.ForeignKey(
        CharacterReference, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pending_profiles",
    )
    reference_approval = models.JSONField(null=True, blank=True, default=None)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["series", "character_id"], name="unique_series_character_identity"
            ),
            models.UniqueConstraint(
                fields=["series", "position"], name="unique_series_character_position"
            ),
        ]

    def as_cast_entry(self):
        entry = {
            "id": str(self.character_id),
            **{field: getattr(self, field) for field in CHARACTER_PROFILE_FIELDS},
        }
        if self.reference_id:
            entry["reference_id"] = str(self.reference_id)
            if self.reference.image:
                entry["reference_image"] = self.reference.image.url
        if self.reference_job_id:
            entry["reference_job_id"] = str(self.reference_job_id)
        if self.reference_approval is not None:
            entry["reference_approval"] = self.reference_approval
        return entry


class SeriesEpisode(UUIDModel, TimestampedModel):
    objects = SeriesEpisodeQuerySet.as_manager()

    memory_source_hash = models.CharField(max_length=64, blank=True, default="")
    is_canon = models.BooleanField(default=False)
    series = models.ForeignKey(
        VideoSeries, on_delete=models.CASCADE, related_name="episodes"
    )
    video = models.OneToOneField(
        Video,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="series_episode",
    )
    number = models.PositiveIntegerField()
    idea = models.TextField(max_length=2000)
    summary = models.TextField(max_length=800, blank=True)
    profile_snapshot = models.JSONField(default=dict)
    generation_params = models.JSONField(default=dict)

    @cached_property
    def script_snapshot(self):
        return video_script_snapshot(self.video) if self.video_id else None

    @property
    def script_hash(self):
        return (
            self.script_snapshot["hash"]
            if self.script_snapshot
            else self.memory_source_hash
        )

    @property
    def memory_needs_review(self):
        return bool(
            self.video_id
            and self.summary
            and self.script_hash != self.memory_source_hash
        )

    @property
    def can_update_memory(self):
        return bool(
            self.script_snapshot
            and self.script_snapshot["entries"]
            and self.video.status != VideoStatus.GENERATION
        )

    @property
    def can_retry(self):
        return bool(
            self.video
            and self.video.status == VideoStatus.FAILED
            and not self.video.gpt_answer
        )

    class Meta:
        db_table = "videomanagement_seriesepisode"
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(
                fields=["series", "number"], name="unique_series_episode_number"
            )
        ]
