"""Keep series metadata in sync with the shared video pipeline."""

from .memory import storyboard_snapshot
from .models import SeriesEpisode


def prepare_episode_storyboard(*, video, storyboard, new_script):
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


def mark_episode_canon(*, video):
    if (
        video.status in ("READY", "COMPLETED")
        and (video.settings or {}).get("creation_mode") == "SERIES"
    ):
        SeriesEpisode.objects.using(video._state.db).filter(video=video).update(
            is_canon=True
        )
