from .file_utils import select_music, select_background
from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip, ImageClip, VideoFileClip, vfx,\
    concatenate_videoclips, CompositeVideoClip
from ..models import *
from PIL import Image
import subprocess
import shlex
import os
from .SadTalker.inference import lip


def make_video(video, music=True, avatar=True):
    template = video.prompt.template
    silent = AudioFileClip(r'media\media\sound_effects\blank.wav')
    black = ImageClip(r'media\media\stock_images\black.jpg')
    sounds = Scene.objects.filter(prompt = video.prompt)
    dir_name = video.dir_name
    background = select_background(template.category)

    clip = ImageClip(background.file.path)
    w, h = clip.size
    sound_list = []
    vids = []

    for sound in sounds:
        audio = AudioFileClip(sound.file.path)
        if sound.is_last:
            audio = concatenate_audioclips([audio, silent, silent])

        sound_list.append(audio)
        scenes = SceneImage.objects.filter(scene = sound)

        if scenes.count() > 0:
            for x in scenes:
                if 'jpg' in x.file.path or 'jpeg' in x.file.path or 'png' in x.file.path:
                    Image.open(x.file.path).convert('RGB').resize((int(w*0.65), int(h*0.65))).save(x.file.path)
                    image = ImageClip(x.file.path)
                    image = image.set_duration(audio.duration/len(scenes))
                    image = image.fadein(image.duration*0.2).\
                        fadeout(image.duration*0.2)
                    vids.append(image)

                else:
                    vids.append(black.set_duration(audio.duration))
        else:
            vids.append(black.set_duration(audio.duration))
    final_video = concatenate_videoclips(vids).margin(top=background.image_pos_top, left = background.image_pos_left,
                                                      opacity=4)

    final_audio = concatenate_audioclips(sound_list)
    final_audio.write_audiofile(rf"{dir_name}\output_audio.wav")

    if music:
        selected_music = select_music(template.category)
        if selected_music:
            music = AudioFileClip(selected_music.file.path).volumex(0.07)
            if music.duration > final_audio.duration:
                music = music.subclip(0, final_audio.duration)

            music = music.audio_fadein(4).audio_fadeout(4)
            final_audio = CompositeAudioClip([final_audio, music])

    clip = clip.set_duration(final_audio.duration).set_audio(final_audio)

    color = [int(x) for x in background.color.split(',')]

    masked_clip = clip.fx(vfx.mask_color, color = color, thr = background.through, s = 7)

    final_clip = CompositeVideoClip([final_video,
                                    masked_clip.set_duration(final_audio.duration)],
                                    size = (1920, 1080)).fadein(2).fadeout(2)

    if avatar and video.avatar:
        avatar_video = create_avatar_video(video.avatar, dir_name)
        avatar_vid = VideoFileClip(avatar_video).without_audio().set_position(("right", "bottom")).resize(1.5).\
            fadeout(2)
        final_clip = CompositeVideoClip([final_clip, avatar_vid], size = (1920, 1080))

    intro = Intro.objects.filter(category = template.category)
    outro = Outro.objects.filter(category = template.category)

    if intro and outro:
        intro = VideoFileClip(intro[0].file.path)
        outro = VideoFileClip(outro[0].file.path)
        final_video = concatenate_videoclips([intro, final_clip, outro], method='compose')

    final_video.write_videofile(rf"{dir_name}\output_video.mp4", fps = 24, threads = 8)

    for sound in sound_list:
        sound.close()

    video.output = rf"{dir_name}\output_video.mp4"
    video.status = "COMPLETED"
    video.save()
    return video


def create_avatar_video(avatar, dir_name):
    avatar_cam = lip(source_image = avatar.file.path,
                     driven_audio = rf"{dir_name}\output_audio.wav",
                     result_dir = dir_name, facerender = "pirender", )

    output = rf'{os.getcwd()}\{dir_name}\output_avatar.mp4'
    subprocess.run(shlex.split(
        f'ffmpeg -i "{os.getcwd()}/{avatar_cam}" -vcodec h264  "{output}"'))

    return output
