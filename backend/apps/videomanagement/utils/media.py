import logging
import os
import uuid

from pytubefix import Playlist, YouTube

from .exceptions import FileNotDownloadedException
from ..models import Music

logger = logging.getLogger(__name__)


def download_playlist(url: str, category: str) -> None:
    """
    Download a playlist of videos as audio files and save them as MP3 files.

    Parameters:
    -----------
    url : str
        The URL of the playlist.
    category : str
        The category of the playlist.

    Returns:
    --------
    None

    Notes:
    ------
    - This function uses pytube library to download each video in the playlist as an audio file (MP3).
    - The downloaded audio files are saved in the 'media/music' directory.
    - Each downloaded audio file is renamed with a unique filename generated using uuid.
    - Information about each downloaded music file is stored in the Music model.
    """

    playlist = Playlist(url)
    for music in playlist.videos:
        try:
            stream = music.streams.filter(only_audio=True).first()
            if stream is None:
                raise FileNotDownloadedException()

            filename = str(uuid.uuid4())
            song = stream.download("media/music")
            new_file = f"media/music/{filename}.mp3"
            if not song or not os.path.isfile(song):
                raise FileNotDownloadedException()

            os.rename(song, new_file)

            # No category kwarg: Music has no such field, so every save raised a
            # TypeError and the whole playlist was silently dropped.
            Music.objects.create(name=stream.title, file=new_file)

        except Exception as exc:
            logger.error("Error downloading song: %s", exc)


def download_video(url: str, dir_name: str, *args, **kwargs) -> str:
    """
    Download a video from YouTube.

    Parameters:
    -----------
    url : str
        The URL of the video.
    dir_name : str
        The directory path where the downloaded video will be saved.

    Returns:
    --------
    str
        The path to the downloaded video file.

    Notes:
    ------
    - This function uses the pytube library to download the video from the provided YouTube URL.
    - The downloaded video is saved in the specified directory path.
    - The file name of the downloaded video is based on the video's title.
    """

    yt = YouTube(url)
    video = yt.streams.get_highest_resolution()

    return video.download(dir_name)


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
