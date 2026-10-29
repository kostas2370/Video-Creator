"""Keep series metadata in sync with the shared video pipeline."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.videomanagement.domain_signals import storyboard_generated
from apps.videomanagement.models import Video

from .memory import storyboard_snapshot
from .models import SeriesEpisode


@receiver(storyboard_generated, sender=Video)
def episode_storyboard_generated(sender, video, storyboard, new_script, **kwargs):
    if (video.settings or {}).get("creation_mode") != "SERIES":
        return
    episodes = SeriesEpisode.objects.using(video._state.db)
    episode = episodes.filter(video=video).first()
    if episode is None:
        return
    video.settings.update(
        creation_mode="SERIES",
        series_id=str(episode.series_id),
        series_title=episode.profile_snapshot.get("title", "Series"),
        episode_number=episode.number,
    )
    if new_script and isinstance(storyboard.get("episode_summary"), str):
        episodes.filter(pk=episode.pk, summary="").update(
            summary=storyboard["episode_summary"].strip()[:800],
            memory_source_hash=storyboard_snapshot(storyboard)["hash"],
        )


@receiver(post_save, sender=Video)
def episode_video_saved(sender, instance, using, raw=False, **kwargs):
    if (
        not raw
        and instance.status in ("READY", "COMPLETED")
        and (instance.settings or {}).get("creation_mode") == "SERIES"
    ):
        SeriesEpisode.objects.using(using).filter(video=instance).update(is_canon=True)
