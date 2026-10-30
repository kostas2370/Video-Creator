import tempfile

from django.core.files import File
from pytubefix import YouTube

from apps.common.youtube import download_youtube_video
from apps.videomanagement.models import Music


def download_video(url: str, dir_name: str, *args, **kwargs) -> str:
    """Download a YouTube video with audio through the shared downloader."""
    path, _title = download_youtube_video(url, dir_name)
    return str(path)


def download_music(url: str) -> Music | None:
    """Reuse a saved track or download its audio in the original format."""
    if url in (None, "", "None"):
        return None

    title = str(YouTube(url).title)[:140]
    existing = Music.objects.filter(name=title).first()
    if existing:
        return existing

    with tempfile.TemporaryDirectory() as directory:
        path, title = download_youtube_video(url, directory, audio_only=True)
        music = Music(name=title[:140])
        with path.open("rb") as audio:
            music.file.save(path.name, File(audio))
        return music
