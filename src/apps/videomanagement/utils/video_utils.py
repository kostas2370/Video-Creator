import os
import shlex
import subprocess
import uuid
import logging
from PIL import Image
from django.db.models import QuerySet
from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip, ImageClip, VideoFileClip, vfx, \
    concatenate_videoclips, CompositeVideoClip, TextClip

from .SadTalker.inference import lip
from ..models import *
from .exceptions import RenderFailedException


logger = logging.getLogger(__name__)


def check_if_image(path: str) -> bool:
    supported_image_extensions = {'.jpg', '.jpeg', '.png'}
    file_extension = os.path.splitext(path)[1].lower()
    return file_extension in supported_image_extensions


def check_if_video(path: str) -> bool:
    supported_video_extensions = {'.mp4', '.avi'}
    file_extension = os.path.splitext(path)[1].lower()
    return file_extension in supported_video_extensions


def handle_audio(scene: Scene, scene_image: SceneImage):
    """
    Processes and returns the appropriate audio clip based on the given scene and scene image.

    Args:
        scene (Scene): The scene object containing metadata and file path for the audio.
        scene_image (SceneImage): The scene image object containing the file path and an indicator if it includes audio.

    Returns:
        AudioFileClip: The processed audio clip for the scene, which may be a combination of the scene's audio,
                       the scene image's audio, and silence if applicable.
    """

    silent = AudioFileClip('assets/blank.wav')

    audio = None

    if scene.file:
        try:
            audio = AudioFileClip(scene.file.path)
        except Exception as e:
            logger.error(f"Error loading scene audio: {e}")

    if scene_image and scene_image.with_audio:
        try:
            dump_video = VideoFileClip(scene_image.file.path)
            scene_audio = dump_video.audio
            if audio:
                audio = CompositeAudioClip([audio, scene_audio])
            else:
                audio = scene_audio
        except Exception as e:
            logger.error(f"Error processing scene image audio: {e}")

    if scene_image and scene.is_last and not scene_image.with_audio:
        audio = concatenate_audioclips([audio, silent, silent])

    if audio is None:
        audio = silent

    return audio


def handle_image(audio, scene_image, background):
    """
    Processes and returns the appropriate image clip based on the given audio and scene image.

    Args:
        audio (AudioFileClip): The audio clip associated with the scene.
        scene_image (SceneImage): The scene image object containing the file path.
        background (Background): A background object that contains a file of the background image.


    Returns:
        ImageClip: The processed image clip for the scene, which may include resizing, duration adjustment,
                   and fade effects, or a default black image clip in case of an error.
    """
    if background:
        clip = ImageClip(background.file.path)
        w, h = clip.size
        Image.open(scene_image.file.path).convert('RGB').resize((int(w*0.65), int(h*0.65))).save(scene_image.file.path)
    try:
        image = ImageClip(scene_image.file.path)
        image = image.set_duration(audio.duration)
        image = image.fadein(image.duration*0.2).fadeout(image.duration*0.2)
    except Exception as exc:
        raise Exception(f"Error handling image: {exc}")

    return image


def handle_video(audio: AudioFileClip, scene_image: SceneImage) -> VideoFileClip:
    """
    Processes and returns the appropriate video clip based on the given audio and scene image.

    Args:
        audio (AudioFileClip): The audio clip associated with the scene.
        scene_image (SceneImage): The scene image object containing the file path to the video file.

    Returns:
        VideoFileClip: The processed video clip for the scene, which includes duration adjustment and fade effects.
    """
    try:
        vid_scene = VideoFileClip(scene_image.file.path).without_audio()

    except Exception as e:
        raise ValueError(f"Error loading video file at {scene_image.file.path}: {e}")

    if vid_scene.duration > audio.duration:
        vid_scene = vid_scene.subclip(0, audio.duration)

    vid_scene = vid_scene.fadein(vid_scene.duration*0.2).fadeout(vid_scene.duration*0.2)
    return vid_scene


def process_scene(scene_image: SceneImage, audio, background: Background):
    """
    Processes and returns the appropriate visual clip (image or video) based on the given scene image and audio.

    This function handles the scene by:
    1. Creating a default black video clip with the duration of the audio.
    2. Checking if the scene image is an image or a video.
    3. Processing the scene image as an image or video accordingly.
    4. Returning the processed visual clip.

    Args:
        scene_image (SceneImage): The scene image object containing the file path to the image or video file.
        audio (AudioFileClip): The audio clip associated with the scene.
        background (bool): A flag indicating if the image should be resized as a background.

    Returns:
        VideoFileClip: The processed visual clip for the scene, which may be a black video, an image clip,
                       or a video clip based on the scene image file type.
    """
    black_clip = ImageClip('assets/black.jpg').set_duration(audio.duration)

    file_path = scene_image.file.path

    if not scene_image or not scene_image.file:
        return black_clip
    try:
        if check_if_image(scene_image.file.path):
            return handle_image(audio, scene_image, background)

        if check_if_video(scene_image.file.path):
            return handle_video(audio, scene_image)

    except Exception as exc:
        logger.warning(exc)

    logger.warning(f"Warning: Unsupported file type for {file_path}. Returning black clip.")

    return black_clip


def handle_avatar_video(video, final_video):
    """
    Adds an avatar video to the final video, positioning it at the top right and applying fade-in and fade-out effects.

    This function handles the addition of an avatar video by:
    1. Checking if the avatar video file exists; if not, it creates the avatar video.
    2. Loading the avatar video, removing its audio, resizing it, and applying fade effects.
    3. Compositing the avatar video onto the final video at the specified position and size.

    Args:
        video (Video): The video object containing metadata and the directory name for the avatar video.
        final_video (VideoFileClip): The final video clip onto which the avatar video will be composited.

    Returns:
        VideoFileClip: The final video clip with the avatar video composited at the top right corner, with fade-in
                       and fade-out effects applied.
    """

    avatar_video = f'{os.getcwd()}/{video.dir_name}/output_avatar.mp4'

    if not os.path.exists(f'{os.getcwd()}/{video.dir_name}/output_avatar.mp4'):
        logger.info("Start creating the avatar video")
        avatar_video = create_avatar_video(video.avatar, video.dir_name)

    position = tuple(video.settings.get("avatar_position", "right,top").split(","))
    avatar_vid = VideoFileClip(avatar_video).without_audio().set_position(position).resize(1.5).fadein(2).fadeout(2)

    final_video = CompositeVideoClip([final_video, avatar_vid], size = (1920, 1080))
    return final_video


def handle_music(video, final_audio):
    """
    Adds background music to the final audio, adjusting the volume and applying fade-in and fade-out effects.

    Args:
        video (Video): The video object containing metadata and the file path for the music.
        final_audio (AudioFileClip): The final audio clip to which the background music will be added.

    Returns:
        AudioFileClip: The final audio clip with the background music added,
        including volume adjustment and fade effects.
    """

    music = AudioFileClip(video.music.file.path)
    music_volume = video.settings.get("music_volume", 0.07)
    music = music.volumex(music_volume)

    if music.duration < final_audio.duration:
        loop_count = int(final_audio.duration//music.duration)+1
        music = concatenate_audioclips([music]*loop_count).subclip(0, final_audio.duration)

    else:
        music = music.subclip(0, final_audio.duration)

    fade_duration = min(4, final_audio.duration*0.1)
    music = music.audio_fadein(fade_duration).audio_fadeout(fade_duration)

    final_audio = CompositeAudioClip([final_audio, music])

    return final_audio


def handle_background(final_audio, background, final_video):
    """
    Adds a background effect to a video clip based on the specified color and threshold.

    Args:
        final_audio (AudioFileClip): The final audio clip to synchronize with the video.
        background (Background): The background object containing color and threshold settings for masking.
        final_video (VideoFileClip): The final video clip onto which the masked video will be composited.

    Returns:
        VideoFileClip: The final video with background effect applied, including masking and fade effects.
    """

    if not background:
        return final_video.resize((1920, 1080))

    if background.file.path.lower().endswith((".jpg", ".png")):
        bg_clip = ImageClip(background.file.path)
    else:
        bg_clip = VideoFileClip(background.file.path).without_audio()

    bg_clip = bg_clip.set_duration(final_audio.duration).resize((1920, 1080))
    mask_color = [int(x) for x in background.color.split(",")]
    threshold = float(background.threshold) / 255.0
    masked_clip = final_video.fx(vfx.mask_color, color=mask_color, thr=threshold, s=7)
    final_video = CompositeVideoClip([bg_clip, masked_clip.set_duration(final_audio.duration)]).crossfadein(2)

    return final_video


def handle_final_video(background, final_audio, final_video, video, subtitles: list):
    """
    Processes and generates the final video clip with optional music, background effect, avatar overlay,
    subtitles, intro, and outro clips.

    Args:
        background (Background or None): Background object containing color and threshold settings for masking,
                                         or None if no background effect is applied.
        final_audio (AudioFileClip): The final audio clip to synchronize with the video.
        final_video (VideoFileClip): The base final video clip to which all components will be added.
        video (Video): The video object containing metadata such as music, avatar, intro, and outro clips.
        subtitles (list of VideoFileClip): A list of subtitle clips to be added to the final video.

    Returns:
        VideoFileClip: The fully processed final video clip with all specified components added.
    """
    final_video = handle_background(final_audio, background, final_video)

    if getattr(video, "music", None):
        final_audio = handle_music(video, final_audio)

    final_video = final_video.set_audio(final_audio)

    if getattr(video, "avatar", None):
        final_video = handle_avatar_video(video, final_video)

    if video.settings.get("subtitles", False) and subtitles:
        subs = concatenate_videoclips(subtitles, method = "compose")
        video_height = final_video.size[1]
        subtitle_position = (60, video_height-150)
        final_video = CompositeVideoClip([final_video, subs.set_pos(subtitle_position).fadein(1).fadeout(1)])

    if getattr(video, "intro", None):
        intro = VideoFileClip(video.intro.file.path).resize(final_video.size)
        final_video = concatenate_videoclips([intro, final_video], method = "compose")

    if getattr(video, "outro", None):
        outro = VideoFileClip(video.outro.file.path).resize(final_video.size)
        final_video = concatenate_videoclips([final_video, outro], method = "compose")

    return final_video


def make_video(video: Video) -> Video:
    """
    Creates a video based on the provided video object, handling scenes, audio, subtitles, background,
    and final video assembly and output.

    Args:
        video (Videos): The video object containing metadata and settings for video creation.

    Returns:
        Videos: The updated video object with output file path and status.
    """

    if video.status not in {"READY", "COMPLETED"}:
        raise RenderFailedException("Video is not in a renderable state.")

    video.status = "RENDERING"
    video.save()

    scenes: Union[QuerySet, list[Scene]] = video.prompt.scenes.all()
    background: Background = video.background
    sound_list, vids, subtitles = [], [], []

    for scene in scenes:
        scene_image = SceneImage.objects.filter(scene=scene).first()
        audio = handle_audio(scene, scene_image)
        sound_list.append(audio)

        if video.settings.get("subtitles", False):
            subtitles.append(create_subtitle_clip(scene.text, audio.duration))

        vids.append(process_scene(scene_image, audio, background))

    if not vids:
        raise RenderFailedException("No video scenes were processed.")

    try:
        final_video = concatenate_videoclips(vids)

        if background:
            final_video = final_video.margin(
                top=background.image_pos_top,
                left=background.image_pos_left,
                opacity=4
            ).set_position("center")

        final_audio = concatenate_audioclips(sound_list)
        final_audio_path = f"{video.dir_name}/output_audio.wav"
        final_audio.write_audiofile(final_audio_path)

        final_video = handle_final_video(background, final_audio, final_video, video, subtitles)
        final_video_path = f"{video.dir_name}/output_video.mp4"
        final_video.write_videofile(final_video_path, fps=24, threads=8)

        video.output = final_video_path
        video.status = "COMPLETED"

    finally:
        for clip in sound_list + vids + subtitles:
            clip.close()
        final_audio.close()
        final_video.close()

    video.save()
    return video


def create_subtitle_clip(text: str, duration: float, fontsize: int = 37, color: str = "blue",
                         bg_color: str = "black", font: str = "Arial", size: tuple = (1600, 500)) -> TextClip:
    """
    Creates a styled subtitle clip.

    Parameters:
    -----------
    text : str
        The subtitle text.
    duration : float
        The duration for which the subtitle should be displayed.
    fontsize : int, optional
        The font size of the text (default: 37).
    color : str, optional
        The color of the text (default: "blue").
    bg_color : str, optional
        The background color of the text box (default: "black").
    font : str, optional
        The font type (default: "Arial").
    size : tuple, optional
        The size of the subtitle box (default: (1600, 500)).

    Returns:
    --------
    TextClip
        A moviepy TextClip styled as a subtitle.
    """
    try:
        return TextClip(
            text, fontsize=fontsize, color=color, font=font, method="caption", size=size,
            bg_color=bg_color
        ).set_duration(duration)
    except Exception as e:
        logger.error(f"Error creating subtitle clip: {e}")
        return None


def create_avatar_video(avatar: Avatar, dir_name: str) -> str:
    """
    Create an avatar video synchronized with an audio file.

    Parameters:
    -----------
    avatar : Avatars
        An instance of the Avatars class containing the avatar image file.
    dir_name : str
        The directory name where the output files are stored.

    Returns:
    --------
    str
        The file path to the created avatar video.

    Detailed Steps:
    ---------------
    1. Use the `lip` function to generate a video of the avatar synchronized with the audio file.
    2. Use ffmpeg to encode the generated video with the h264 codec and save it to the specified directory.

    Notes:
    ------
    - Requires the `lip` function and ffmpeg to be properly installed and configured.
    - The `lip` function should generate the avatar video and save it in the specified directory.
    """

    try:
        avatar_cam = lip(source_image = avatar.file.path, driven_audio = os.path.join(dir_name, "output_audio.wav"),
                         result_dir = dir_name, facerender = "pirender", )
    except Exception as e:
        logger.error(f"Error running lip function: {e}")
        return ""

    output = os.path.join(os.getcwd(), dir_name, "output_avatar.mp4")

    ffmpeg_command = f'ffmpeg -i "{os.path.join(os.getcwd(), avatar_cam)}" -vcodec h264 "{output}"'
    try:
        result = subprocess.run(shlex.split(ffmpeg_command), stdout = subprocess.PIPE, stderr = subprocess.PIPE,
                                text = True)
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return ""
    except Exception as e:
        logger.error(f"Error executing ffmpeg: {e}")
        return ""

    return output


def split_video_and_mp3(video_path: str) -> tuple[str, str]:
    """
    Split a video file into separate video and audio files.

    Parameters:
    -----------
    video_path : str
        The file path to the original video file.

    Returns:
    --------
    tuple[str, str]
        A tuple containing the file paths to the saved audio (mp3) and video (mp4) files.

    Detailed Steps:
    ---------------
    1. Determine the folder to save the new audio and video files.
    2. Load the video file using VideoFileClip.
    3. Generate unique file names for the audio and video files.
    4. Extract and save the audio from the video as an mp3 file.
    5. Remove the audio from the video and save the new video file.
    6. Remove the original video file.
    7. Return the paths to the saved audio and video files.

    Notes:
    ------
    - Requires the moviepy library.
    - The function assumes the existence of 'dialogues' and
     'images' directories within the folder of the original video file.
    - The original video file is deleted after processing.
    """

    folder_to_save = os.path.split(os.path.abspath(video_path))[0]
    video = VideoFileClip(video_path)

    audio_save = f'{str(folder_to_save)}/dialogues/{str(uuid.uuid4())}.mp3'
    video_save = f'{str(folder_to_save)}/images/{str(uuid.uuid4())}.mp4'

    try:
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_save)
        video_without_audio = video.set_audio(None)
        video_without_audio.write_videofile(video_save, codec = "libx264", audio = False)

    except Exception as e:
        logger.error(f"Error processing video '{video_path}': {e}")
        return "", ""

    finally:
        if 'video' in locals():
            video.close()
        if 'video_without_audio' in locals():
            video_without_audio.close()
        os.remove(video_path)

    return audio_save, video_save


def add_text_to_video(video: str, text: str, fontcolor: str = "black", fontsize: int = 50, x: str = "(w-text_w)/2",
                      y: str = "h-text_h-20") -> str:
    """
    Add text to a video at a specified position and return the new video file path.

    Parameters:
    -----------
    video : str
        The file path to the original video.
    text : str
        The text to be added to the video.
    fontcolor : str, optional
        The color of the text. Default is "black".
    fontsize : int, optional
        The size of the text font. Default is 50.
    x : str, optional
        The x-coordinate position for the text (FFmpeg expression). Default is centered.
    y : str, optional
        The y-coordinate position for the text (FFmpeg expression). Default is near the bottom.

    Returns:
    --------
    str
        The file path to the new video with the added text.

    Detailed Steps:
    ---------------
    1. Generate a new file name for the video with the added text.
    2. Construct the ffmpeg command to add text to the video.
    3. Execute the ffmpeg command using subprocess.
    4. Remove the original video file if successful.
    5. Return the file path to the new video.

    Notes:
    ------
    - Requires ffmpeg to be installed and available in the system path.
    - The original video file is deleted only if the new video is successfully created.
    """

    base_dir, ext = os.path.splitext(video)
    output_video = f"{base_dir}_{uuid.uuid4().hex}.mp4"

    command = [
        "ffmpeg", "-i", video,
        "-vf", f"drawtext=fontsize={fontsize}:fontcolor={fontcolor}:text='{text}':"
               f"x={x}:y={y}:shadowcolor=black:shadowx=2:shadowy=2:"
               f"box=1:boxcolor=black@0.5:boxborderw=10",
        "-y", output_video
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return ""

        os.remove(video)
        return output_video

    except Exception as e:
        logger.error(f"Error processing video: {e}")
        return ""
