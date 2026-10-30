import os
import uuid

from pytubefix import YouTube

from apps.common.youtube import download_youtube_video
from apps.videomanagement.models import Music


def download_video(url: str, dir_name: str, *args, **kwargs) -> str:
    """Download a YouTube video with audio through the shared downloader."""
    path, _title = download_youtube_video(url, dir_name)
    return str(path)


def download_music(url: str) -> str:
    """
    Download music from YouTube and save it as an MP3 file.

    Parameters:
    -----------
    url : str
        The URL of the YouTube video containing the music.

    Returns:
    --------
    str
        The path to the downloaded MP3 file, or None if the URL is invalid.

    Notes:
    ------
    - This function downloads the audio from the provided YouTube video URL.
    - The downloaded audio is saved as an MP3 file in the 'media/music' directory.
    - If the same music is already downloaded, it returns the existing Music object without downloading again.
    """

    if url in (None, "", "None"):
        return None

    yt = YouTube(url)

    video = yt.streams.filter(only_audio=True).first()
    existing = Music.objects.filter(name=video.title)
    if existing.count() > 0:
        return existing.first()

    video = video.download("media/music")
    filename = str(uuid.uuid4())
    new_file = f"media/music/{filename}.mp3"
    os.rename(video, new_file)
    mus = Music.objects.create(name=yt.title, file=new_file)
    return mus
