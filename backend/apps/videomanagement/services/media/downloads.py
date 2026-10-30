import tempfile

from django.core.files import File

from apps.common.youtube import download_youtube_video, youtube_url
from apps.videomanagement.models import Music


def download_video(url: str, dir_name: str, *args, **kwargs) -> str:
    """Download a YouTube video with audio through the shared downloader."""
    path, _title = download_youtube_video(url, dir_name)
    return str(path)


def download_music(url: str, *, user) -> Music | None:
    """Reuse a saved track or download its audio in the original format."""
    if url in (None, "", "None"):
        return None

    if user is None:
        raise ValueError("A music download requires an owner.")
    url = youtube_url(url)
    video_id = url.rsplit("=", 1)[1]
    existing = Music.objects.filter(created_by=user, youtube_video_id=video_id).first()
    if existing and existing.file and existing.file.storage.exists(existing.file.name):
        return existing

    with tempfile.TemporaryDirectory() as directory:
        path, title = download_youtube_video(url, directory, audio_only=True)
        music = existing or Music(created_by=user, youtube_video_id=video_id)
        music.name = title[:140]
        with path.open("rb") as audio:
            music.file.save(path.name, File(audio), save=False)
        try:
            music.save()
        except Exception:
            music.file.storage.delete(music.file.name)
            raise
        return music
