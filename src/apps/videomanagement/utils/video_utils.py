from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip, ImageClip, VideoFileClip, vfx,\
    concatenate_videoclips, CompositeVideoClip, TextClip
from ..models import *
from PIL import Image
import subprocess
import shlex
import os
from .SadTalker.inference import lip
import uuid


def check_if_image(path: str) -> bool:
    """
    Check if the given file path corresponds to an image file.

    Parameters:
    -----------
    path : str
        The file path to check.

    Returns:
    --------
    bool
        True if the file is an image, False otherwise.

    Notes:
    ------
    - This function checks the file extension against a predefined list of image extensions (e.g., 'jpg', 'jpeg', 'png').
    - The check is case-insensitive.
    """

    image_extensions = ['jpg', 'jpeg', 'png']
    for x in image_extensions:
        if x in path:
            return True
    return False


def check_if_video(path: str) -> bool:
    """
    Check if the given file path corresponds to a video file.

    Parameters:
    -----------
    path : str
        The file path to check.

    Returns:
    --------
    bool
        True if the file is a video, False otherwise.

    Notes:
    ------
    - This function checks the file extension against a predefined list of video extensions (e.g., 'mp4', 'avi').
    - The check is case-insensitive.
    """

    image_extensions = ['mp4',  'avi']
    for x in image_extensions:
        if x in path:
            return True
    return False


def make_video(video: Videos, subtitle: bool = False) -> Videos:
    """
    Create a composite video based on provided video object and optional subtitles.

    Parameters:
    -----------
    video : Videos
        An instance of the Videos class containing video details, including prompts, background, music, intro, and outro.
    subtitle : bool, optional
        A flag indicating whether to include subtitles in the video. Default is False.

    Returns:
    --------
    Videos
        The updated video instance with the output video file path and status set to "COMPLETED".

    Detailed Steps:
    ---------------
    1. Load silent audio and black image files as defaults.
    2. Retrieve sound scenes associated with the video's prompt and background image (if available).
    3. Initialize lists to store audio clips, video clips, and subtitles.
    4. Process each sound scene:
        a. Create an audio clip and append to the sound list.
        b. Generate subtitles if the subtitle flag is True and append to the subtitles list.
        c. Retrieve associated scene images or videos, resize if necessary, and append to the video clips list.
    5. Concatenate video clips and apply margins or set position based on background availability.
    6. Concatenate audio clips and optionally overlay background music.
    7. Combine video and audio clips, applying masks, fades, and resizing as required.
    8. Optionally, add an avatar video overlay.
    9. Add subtitles if the subtitle flag is True.
    10. Prepend intro and append outro videos if available.
    11. Write the final composite video to the output path and close all resources.
    12. Update the video object with the output file path and status, then save.

    Notes:
    ------
    - Requires presence of certain assets (e.g., silent audio file, black image) at specified paths.
    - Uses various external libraries such as moviepy for video/audio processing and PIL for image manipulation.
    """

    silent = AudioFileClip(r'assets\blank.wav')
    black = ImageClip(r'assets\black.jpg')
    sounds = Scene.objects.filter(prompt = video.prompt)
    background = video.background

    if background:
        clip = ImageClip(background.file.path)
        w, h = clip.size

    sound_list = []
    vids = []
    subtitles = []
    for sound in sounds:
        audio = AudioFileClip(sound.file.path)
        if sound.is_last:
            audio = concatenate_audioclips([audio, silent, silent])

        sound_list.append(audio)
        if subtitle:
            sub = TextClip(sound.text, fontsize = 37, color = 'blue', method = "caption", size = (1600, 500)).\
                set_duration(audio.duration)

            subtitles.append(sub)

        scenes = SceneImage.objects.filter(scene = sound)

        if scenes.count() > 0:
            for x in scenes:
                if x.file and check_if_image(x.file.path):
                    if background:
                        Image.open(x.file.path).convert('RGB').resize((int(w*0.65), int(h*0.65))).save(x.file.path)
                    try:
                        image = ImageClip(x.file.path)
                        image = image.set_duration(audio.duration/len(scenes))

                        image = image.fadein(image.duration*0.2).\
                            fadeout(image.duration*0.2)
                    except ValueError:
                        image = black.set_duration(audio.duration)

                    vids.append(image)

                elif x.file and check_if_video(x.file.path):

                    vid_scene = VideoFileClip(x.file.path).without_audio()
                    if vid_scene.duration >= audio.duration:
                        vid_scene = vid_scene.subclip(0, audio.duration)

                    vid_scene = vid_scene.fadein(audio.duration*0.2).fadeout(audio.duration*0.2)
                    vids.append(vid_scene)

                else:
                    vids.append(black.set_duration(audio.duration))
        else:
            vids.append(black.set_duration(audio.duration))

    if background:
        final_video = concatenate_videoclips(vids).margin(top=background.image_pos_top,
                                                          left = background.image_pos_left,
                                                          opacity=4)
    else:
        final_video = concatenate_videoclips(vids).set_position('center')

    final_audio = concatenate_audioclips(sound_list)
    final_audio.write_audiofile(rf"{video.dir_name}\output_audio.wav")

    if video.music:
        music = AudioFileClip(video.music.file.path).volumex(0.07)
        music = music.subclip(0, final_audio.duration) if music.duration > final_audio.duration else music
        music = music.audio_fadein(4).audio_fadeout(4)
        final_audio = CompositeAudioClip([final_audio, music])

    if background:
        clip = clip.set_duration(final_audio.duration).set_audio(final_audio)

        color = [int(x) for x in background.color.split(',')]

        masked_clip = clip.fx(vfx.mask_color, color = color, thr = background.through, s = 7)

        final_video = CompositeVideoClip([final_video,
                                         masked_clip.set_duration(final_audio.duration)],
                                         size = (1920, 1080)).fadein(2).fadeout(2)

    else:
        final_video = final_video.set_audio(final_audio).resize((1920, 1080))

    if video.avatar:
        avatar_video = rf'{os.getcwd()}\{video.dir_name}\output_avatar.mp4'
        if not os.path.exists(rf'{os.getcwd()}\{video.dir_name}\output_avatar.mp4'):
            avatar_video = create_avatar_video(video.avatar, video.dir_name)
        avatar_vid = VideoFileClip(avatar_video).without_audio().set_position(("right", "top")).resize(1.5).\
            fadein(2).fadeout(2)
        final_video = CompositeVideoClip([final_video, avatar_vid], size = (1920, 1080))

    if subtitle:
        subs = concatenate_videoclips(subtitles)
        final_video = CompositeVideoClip([final_video, subs.set_pos((60, 760)).fadein(1).fadeout(1)])

    if video.intro:
        intro = VideoFileClip(video.intro.file.path)
        final_video = concatenate_videoclips([intro, final_video], method='compose')

    if video.outro:
        outro = VideoFileClip(video.outro.file.path)
        final_video = concatenate_videoclips([final_video, outro], method='compose')

    final_video.write_videofile(rf"{video.dir_name}\output_video.mp4", fps = 24, threads = 8)

    for sound in sound_list:
        sound.close()

    for vid in vids:
        vid.close()

    video.output = rf"{video.dir_name}\output_video.mp4"
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

    avatar_cam = lip(source_image = avatar.file.path,
                     driven_audio = rf"{dir_name}\output_audio.wav",
                     result_dir = dir_name, facerender = "pirender", )

    output = rf'{os.getcwd()}\{dir_name}\output_avatar.mp4'
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
    - The function assumes the existence of 'dialogues' and 'images' directories within the folder of the original video file.
    - The original video file is deleted after processing.
    """

    folder_to_save = os.path.split(os.path.abspath(video_path))[0]
    video = VideoFileClip(video_path)
    audio_save = f'{str(folder_to_save)}/dialogues/{str(uuid.uuid4())}.mp3'
    video_save = f'{str(folder_to_save)}/images/{str(uuid.uuid4())}.mp4'

    video.audio.write_audiofile(audio_save)

    video_without_audio = video.set_audio(None)
    video_without_audio.write_videofile(video_save)
    os.remove(video_path)
    return audio_save, video_save


def add_text_to_video(video: str, text: str, fontcolor: str = "blue", fontsize: int = 50,
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
    command = f"ffmpeg -i \"{video}\" -vf \" drawtext =fontsize={fontsize}: fontcolor = {fontcolor}:text='{text}': " \
              f"x = {x}: y= {y} \" \"{video_name}\""

    os.system(command)
    os.remove(video)
    return video_name
