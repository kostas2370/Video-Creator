"""
Viddie is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Viddie is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
"""


from .file_utils import select_music, select_background
from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip, ImageClip, VideoFileClip, vfx,\
    concatenate_videoclips, CompositeVideoClip, TextClip
from ..models import *
from PIL import Image
import subprocess
import shlex
import os
from .SadTalker.inference import lip
from django.db.models import Q


def make_video(video, subtitle=False):
    silent = AudioFileClip(r'assets\blank.wav')
    black = ImageClip(r'assets\black.jpg')
    sounds = Scene.objects.filter(prompt = video.prompt)
    category = video.prompt.template.category if video.prompt.template else None
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
                if 'jpg' in x.file.path or 'jpeg' in x.file.path or 'png' in x.file.path:
                    if background:
                        Image.open(x.file.path).convert('RGB').resize((int(w*0.65), int(h*0.65))).save(x.file.path)

                    image = ImageClip(x.file.path)
                    image = image.set_duration(audio.duration/len(scenes))
                    image = image.fadein(image.duration*0.2).\
                        fadeout(image.duration*0.2)
                    vids.append(image)

                elif "mp4" in x.file.path or "avi" in x.file.path:

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
        final_video = concatenate_videoclips(vids).margin(top=background.image_pos_top, left = background.image_pos_left,
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

    intro = Intro.objects.filter(Q(category = category) | Q(category="OTHER"))
    outro = Outro.objects.filter(Q(category = category) | Q(category="OTHER"))

    if intro and outro:
        intro = VideoFileClip(intro[0].file.path)
        outro = VideoFileClip(outro[0].file.path)
        final_video = concatenate_videoclips([intro, final_video, outro], method='compose')

    final_video.write_videofile(rf"{video.dir_name}\output_video.mp4", fps = 24, threads = 8)

    for sound in sound_list:
        sound.close()

    video.output = rf"{video.dir_name}\output_video.mp4"
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
