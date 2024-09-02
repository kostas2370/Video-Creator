import os
import shlex
import subprocess
import uuid

from PIL import Image
from django.db.models import QuerySet
from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip, ImageClip, VideoFileClip, vfx, \
    concatenate_videoclips, CompositeVideoClip, TextClip

from .SadTalker.inference import lip
from ..models import *
from .exceptions import RenderFailedException


def check_if_image(path: str) -> bool:
    accepted_image_extensions = ('jpg', 'jpeg', 'png')
    return path.lower().endswith(accepted_image_extensions)


def check_if_video(path: str) -> bool:
    accepted_video_extensions = ('mp4',  'avi')
    return path.lower().endswith(accepted_video_extensions)


def handle_audio(scene: Scene, scene_image: SceneImage):
    """
    Processes and returns the appropriate audio clip based on the given scene and scene image.

    This function handles the audio for a given scene by:
    1. Loading an audio file from the scene if available.
    2. Adding audio from the scene image if it includes audio.
    3. Appending silent audio if the scene is the last one and the scene image does not include audio.

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
        audio = AudioFileClip(scene.file.path)

    if scene_image and scene_image.with_audio:
        dump_video = VideoFileClip(scene_image.file.path)
        if audio:
            audio = CompositeAudioClip([audio, dump_video.audio])
        else:
            audio = dump_video.audio

    if scene_image and scene.is_last and not scene_image.with_audio:
        audio = concatenate_audioclips([audio, silent, silent])

    return audio


def handle_image(audio, scene_image, background):
    """
    Processes and returns the appropriate image clip based on the given audio and scene image.

    This function handles the image for a given scene by:
    1. Resizing and saving the scene image if a background is provided.
    2. Creating an ImageClip from the scene image file.
    3. Setting the duration of the image clip to match the audio duration.
    4. Applying fade-in and fade-out effects to the image clip.
    5. Using a black image clip if there's an issue with the scene image file.

    Args:
        audio (AudioFileClip): The audio clip associated with the scene.
        scene_image (SceneImage): The scene image object containing the file path.
        background (bool): A flag indicating if the image should be resized as a background.


    Returns:
        ImageClip: The processed image clip for the scene, which may include resizing, duration adjustment,
                   and fade effects, or a default black image clip in case of an error.
    """
    black = ImageClip('assets/black.jpg')

    clip = None
    if background:
        clip = ImageClip(background.file.path)
        w, h = clip.size
        Image.open(scene_image.file.path).convert('RGB').resize((int(w*0.65), int(h*0.65))).save(scene_image.file.path)
    try:
        image = ImageClip(scene_image.file.path)
        image = image.set_duration(audio.duration)

        image = image.fadein(image.duration*0.2).fadeout(image.duration*0.2)
    except ValueError:
        image = black.set_duration(audio.duration)

    return image


def handle_video(audio, scene_image: SceneImage):
    """
    Processes and returns the appropriate video clip based on the given audio and scene image.

    This function handles the video for a given scene by:
    1. Loading a video file from the scene image and removing its audio.
    2. Adjusting the duration of the video to match the audio duration, trimming it if necessary.
    3. Applying fade-in and fade-out effects to the video clip.

    Args:
        audio (AudioFileClip): The audio clip associated with the scene.
        scene_image (SceneImage): The scene image object containing the file path to the video file.

    Returns:
        VideoFileClip: The processed video clip for the scene, which includes duration adjustment and fade effects.
    """

    vid_scene = VideoFileClip(scene_image.file.path).without_audio()

    if vid_scene.duration > audio.duration:
        vid_scene = vid_scene.subclip(0, audio.duration)

    vid_scene = vid_scene.fadein(vid_scene.duration*0.2).fadeout(vid_scene.duration*0.2)
    return vid_scene


def process_scene(scene_image, audio, background, black):
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
        black (VideoFileClip): A default black video clip to use in case the scene image is not available.

    Returns:
        VideoFileClip: The processed visual clip for the scene, which may be a black video, an image clip,
                       or a video clip based on the scene image file type.
    """

    vid_scene = black.set_duration(audio.duration)

    if not scene_image or not scene_image.file:
        return vid_scene

    if check_if_image(scene_image.file.path):
        return handle_image(audio, scene_image, background)

    if check_if_video(scene_image.file.path):
        return handle_video(audio, scene_image)

    return vid_scene


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
        avatar_video = create_avatar_video(video.avatar, video.dir_name)

    position = tuple(video.settings.get("avatar_position", "right,top").split(","))
    avatar_vid = VideoFileClip(avatar_video).without_audio().set_position(position).resize(1.5).fadein(2).fadeout(2)

    final_video = CompositeVideoClip([final_video, avatar_vid], size = (1920, 1080))
    return final_video


def handle_music(video, final_audio):
    """
    Adds background music to the final audio, adjusting the volume and applying fade-in and fade-out effects.

    This function handles the addition of background music by:
    1. Loading the music file associated with the video and adjusting its volume.
    2. Trimming the music to match the duration of the final audio if necessary.
    3. Applying fade-in and fade-out effects to the music.
    4. Combining the final audio with the background music into a composite audio clip.

    Args:
        video (Video): The video object containing metadata and the file path for the music.
        final_audio (AudioFileClip): The final audio clip to which the background music will be added.

    Returns:
        AudioFileClip: The final audio clip with the background music added, including volume adjustment and fade effects.
    """

    music = AudioFileClip(video.music.file.path).volumex(0.07)
    music = music.subclip(0, final_audio.duration) if music.duration > final_audio.duration else music
    music = music.audio_fadein(4).audio_fadeout(4)
    final_audio = CompositeAudioClip([final_audio, music])

    return final_audio


def handle_background(final_audio, background, final_video):
    """
    Adds a background effect to a video clip based on the specified color and threshold.

    This function handles the addition of a background effect by:
    1. Setting the duration of the video clip to match the duration of the final audio and applying the final audio.
    2. Masking the video clip to replace the specified color with transparency, based on the provided threshold.
    3. Compositing the masked video clip onto the final video, adjusting its size, and applying fade-in and fade-out effects.

    Args:
        clip (VideoFileClip): The video clip to which the background effect will be applied.
        final_audio (AudioFileClip): The final audio clip to synchronize with the video clip.
        background (Background): The background object containing color and threshold settings for masking.
        final_video (VideoFileClip): The final video clip onto which the masked video clip will be composited.

    Returns:
        VideoFileClip: The final video clip with the background effect applied, including masking and fade effects.
    """

    if not background:
        return final_video.resize((1920, 1080))

    clip = ImageClip(background.file.path)

    clip = clip.set_duration(final_audio.duration)
    color = [int(x) for x in background.color.split(',')]
    masked_clip = clip.fx(vfx.mask_color, color = color, thr = background.through, s = 7)

    final_video = CompositeVideoClip([final_video, masked_clip.set_duration(final_audio.duration)],
                                     size = (1920, 1080)).fadein(2).fadeout(2)

    return final_video


def handle_final_video(background, final_audio, final_video, video, subtitles):
    """
    Processes and generates the final video clip with optional music, background effect, avatar overlay,
    subtitles, intro, and outro clips.

    This function handles the assembly of the final video by:
    1. Adding background music if specified in the video metadata.
    2. Applying a background effect if specified in the video metadata, masking a specified color with transparency.
    3. Setting the audio for the final video clip and resizing it to 1920x1080 resolution if no background effect is applied.
    4. Adding an avatar overlay at the top right corner of the final video if specified in the video metadata.
    5. Adding subtitles to the final video, positioned at the bottom left, with fade-in and fade-out effects.
    6. Adding an intro clip at the beginning of the final video if specified in the video metadata.
    7. Adding an outro clip at the end of the final video if specified in the video metadata.

    Args:
        background (Background or None): The background object containing color and threshold settings for masking,
                                         or None if no background effect is applied.
        final_audio (AudioFileClip): The final audio clip to synchronize with the video.
        final_video (VideoFileClip): The base final video clip to which all components will be added.
        video (Video): The video object containing metadata such as music, avatar, intro, and outro clips.
        subtitle (bool): A flag indicating if subtitles should be added to the final video.
        subtitles (list of VideoFileClip): A list of subtitle clips to be added to the final video.

    Returns:
        VideoFileClip: The fully processed final video clip with all specified components added.
    """
    if video.music:
        final_audio = handle_music(video, final_audio)

    final_video = handle_background(final_audio, background, final_video).set_audio(final_audio)

    if video.avatar:
        final_video = handle_avatar_video(video, final_video)

    if video.settings.get("subtitles", False):
        subs = concatenate_videoclips(subtitles)
        final_video = CompositeVideoClip([final_video, subs.set_pos((60, 760)).fadein(1).fadeout(1)])

    if video.intro:
        intro = VideoFileClip(video.intro.file.path)
        final_video = concatenate_videoclips([intro, final_video], method='compose')

    if video.outro:
        outro = VideoFileClip(video.outro.file.path)
        final_video = concatenate_videoclips([final_video, outro], method='compose')

    return final_video


def make_video(video: Videos) -> Videos:
    """
    Creates a video based on the provided video object, handling scenes, audio, subtitles, background,
    and final video assembly and output.

    Args:
        video (Videos): The video object containing metadata and settings for video creation.
        subtitle (bool, optional): Flag indicating whether subtitles should be added to the video. Defaults to False.

    Returns:
        Videos: The updated video object with output file path and status.
    """

    if video.status not in ["READY", "COMPLETED"]:
        raise RenderFailedException

    video.status = "RENDERING"
    video.save()

    black = ImageClip('assets/black.jpg')
    scenes: Union[QuerySet, list[Scene]] = Scene.objects.filter(prompt = video.prompt)
    background: Backgrounds = video.background
    sound_list = []
    vids = []
    subtitles = []
    for scene in scenes:
        scene_image = SceneImage.objects.filter(scene = scene).first()
        audio = handle_audio(scene, scene_image)
        sound_list.append(audio)

        if video.settings.get("subtitles", False):
            sub = TextClip(scene.text, fontsize = 37, color = 'blue', method = "caption", size = (1600, 500)).\
                  set_duration(audio.duration)

            subtitles.append(sub)

        im = process_scene(scene_image, audio, background, black)
        vids.append(im)

    if background:
        final_video = concatenate_videoclips(vids).margin(top=background.image_pos_top,
                                                          left = background.image_pos_left,
                                                          opacity=4)
    else:
        final_video = concatenate_videoclips(vids).set_position('center')

    final_audio = concatenate_audioclips(sound_list)
    final_audio.write_audiofile(f"{video.dir_name}/output_audio.wav")
    final_video = handle_final_video(background, final_audio, final_video, video, subtitles)
    final_video.write_videofile(f"{video.dir_name}/output_video.mp4", fps = 24, threads = 8)

    for sound in sound_list:
        sound.close()

    for vid in vids:
        vid.close()

    final_video.close()
    final_audio.close()

    for sub in subtitles:
        sub.close()

    video.output = f"{video.dir_name}/output_video.mp4"
    video.status = "COMPLETED"
    video.save()
    return video


def create_avatar_video(avatar: Avatars, dir_name: str) -> str:
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

    avatar_cam: str = lip(
        source_image = avatar.file.path,
        driven_audio = f"{dir_name}/output_audio.wav",
        result_dir = dir_name,
        facerender = "pirender", )

    output: str = f'{os.getcwd()}/{dir_name}/output_avatar.mp4'
    subprocess.run(shlex.split(
        f'ffmpeg -i "{os.getcwd()}/{avatar_cam}" -vcodec h264  "{output}"'))

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

    video.audio.write_audiofile(audio_save)

    video_without_audio = video.set_audio(None)
    video_without_audio.write_videofile(video_save)

    video.close()
    video_without_audio.close()

    os.remove(video_path)

    return audio_save, video_save


def add_text_to_video(video: str, text: str, fontcolor: str = "black", fontsize: int = 50,
                      x: int = 500, y: int = 500) -> str:
    """
    Add text to a video at a specified position and return the new video file path.

    Parameters:
    -----------
    video : str
        The file path to the original video.
    text : str
        The text to be added to the video.
    fontcolor : str, optional
        The color of the text. Default is "blue".
    fontsize : int, optional
        The size of the text font. Default is 50.
    x : int, optional
        The x-coordinate position for the text. Default is 500.
    y : int, optional
        The y-coordinate position for the text. Default is 500.

    Returns:
    --------
    str
        The file path to the new video with the added text.

    Detailed Steps:
    ---------------
    1. Generate a new file name for the video with the added text.
    2. Construct the ffmpeg command to add text to the video.
    3. Execute the ffmpeg command.
    4. Remove the original video file.
    5. Return the file path to the new video.

    Notes:
    ------
    - Requires ffmpeg to be installed and available in the system path.
    - The original video file is deleted after the new video is created.
    """

    video_name = video[:-3]+"l.mp4"
    command = (f"ffmpeg -i \"{video}\" -vf \"drawtext=fontsize={fontsize}:fontcolor={fontcolor}:"
               f"text='{text}':x=(w-text_w)/2:y=h-text_h-20:shadowcolor=black:shadowx=2:shadowy=2:"
               f"box=1:boxcolor=black@0.5:boxborderw=10\" \"{video_name}\"")

    os.system(command)
    os.remove(video)
    return video_name
