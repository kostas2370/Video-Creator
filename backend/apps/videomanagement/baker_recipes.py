from model_bakery.recipe import Recipe, foreign_key

from .models import (
    Avatar,
    Background,
    Intro,
    Music,
    Outro,
    Scene,
    SceneImage,
    TemplatePrompt,
    UserPrompt,
    Video,
    VoiceModel,
)

template_prompt = Recipe(
    TemplatePrompt,
    title="a template",
)

user_prompt = Recipe(UserPrompt, prompt="a prompt")

voice_model = Recipe(
    VoiceModel,
    name="a voice",
    provider="open_ai",
    type="API",
    path="onyx",
    sample="https://example.test/sample.wav",
)

avatar = Recipe(
    Avatar,
    name="Natasha",
    gender="female",
    file="media/other/avatars/natasha.jpeg",
    voice=foreign_key(voice_model),
)

music = Recipe(Music, name="a song", file="media/music/song.mp3")

intro = Recipe(Intro, name="an intro", file="media/other/intros/intro.mp4")

outro = Recipe(Outro, name="an outro", file="media/other/outros/outro.mp4")

background = Recipe(
    Background,
    category="EDUCATIONAL",
    name="a background",
    file="media/other/backgrounds/bg.jpg",
    color="0,255,0",
    image_pos_top=10,
    image_pos_left=20,
    avatar_pos_top=30,
    avatar_pos_left=40,
)

scene = Recipe(
    Scene,
    prompt=foreign_key(user_prompt),
    text="a sentence",
    file=None,
    is_last=False,
)

narrated_scene = scene.extend(file="media/speech/line.wav")

last_scene = scene.extend(is_last=True)

scene_image = Recipe(
    SceneImage,
    scene=foreign_key(scene),
    file="media/images/still.png",
    prompt="an image description",
    with_audio=False,
)

video_scene_image = scene_image.extend(file="media/images/clip.mp4")

video_scene_image_with_audio = video_scene_image.extend(with_audio=True)

video = Recipe(
    Video,
    prompt=foreign_key(user_prompt),
    voice_model=foreign_key(voice_model),
    title="a video",
    dir_name="media/videos/a-video",
    gpt_answer="{}",
    status="READY",
    video_type="AI",
    mode="WEB",
    settings=lambda: dict(subtitles=False, narration=True),
)

silent_video = video.extend(settings=lambda: dict(subtitles=False, narration=False))

subtitled_video = video.extend(settings=lambda: dict(subtitles=True, narration=True))

twitch_video = video.extend(video_type="TWITCH", gpt_answer="Source : \n")
