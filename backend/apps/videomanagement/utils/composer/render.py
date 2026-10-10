import logging
from typing import Union

from django.db.models import QuerySet
from moviepy.editor import (
    concatenate_audioclips,
    VideoFileClip,
    concatenate_videoclips,
    CompositeVideoClip,
)

from ...models import (
    RENDERABLE_STATUSES,
    SceneImage,
    Background,
    Scene,
    Video,
    VideoStatus,
)
from ..exceptions import RenderFailedException
from .avatar import handle_avatar_video
from .clips import clip_audio, handle_audio, process_scene
from .layers import fit_to_canvas, handle_background, handle_music
from .transitions import compose_transitions, scene_transition
from .subtitles import create_subtitle_clip
from ...video_formats import output_size

logger = logging.getLogger(__name__)


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
    duration = final_audio.duration if final_audio else final_video.duration
    canvas_size = output_size((video.settings or {}).get("video_format"))
    final_video = handle_background(
        duration, background, final_video, size=canvas_size
    )

    if getattr(video, "music", None):
        final_audio = handle_music(video, final_audio, duration)

    if final_audio:
        final_video = final_video.set_audio(final_audio)

    if getattr(video, "avatar", None):
        final_video = handle_avatar_video(video, final_video)

    if (video.settings or {}).get("subtitles", False) and subtitles:
        subs = concatenate_videoclips(subtitles, method="compose")
        video_height = final_video.size[1]
        subtitle_bottom_margin = int(video_height * 0.05)
        subtitle_y = max(0, video_height - subs.h - subtitle_bottom_margin)
        final_video = CompositeVideoClip(
            [
                final_video,
                subs.set_pos(("center", subtitle_y)).fadein(1).fadeout(1),
            ]
        )

    if getattr(video, "intro", None):
        intro = fit_to_canvas(VideoFileClip(video.intro.file.path), final_video.size)
        final_video = concatenate_videoclips([intro, final_video], method="compose")

    if getattr(video, "outro", None):
        outro = fit_to_canvas(VideoFileClip(video.outro.file.path), final_video.size)
        final_video = concatenate_videoclips([final_video, outro], method="compose")

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

    if video.status not in RENDERABLE_STATUSES:
        raise RenderFailedException("Video is not in a renderable state.")

    video.status = VideoStatus.RENDERING
    video.save()

    scenes: Union[QuerySet, list[Scene]] = video.scenes.all()
    background: Background = video.background
    sound_list, vids, subtitles = [], [], []

    choices = video.settings or {}
    narration = choices.get("narration", True)
    canvas_size = output_size(choices.get("video_format"))

    transitions = []
    for scene in scenes:
        scene_image = SceneImage.objects.filter(scene=scene).first()
        audio = (
            handle_audio(scene, scene_image) if narration else clip_audio(scene_image)
        )

        if audio is not None:
            sound_list.append(audio)

            if narration and choices.get("subtitles", False):
                subtitle = create_subtitle_clip(
                    scene.text,
                    audio.duration,
                    size=(int(canvas_size[0] * 0.84), int(canvas_size[1] * 0.18)),
                )
                if subtitle is not None:
                    subtitles.append(subtitle)

        transitions.append(scene_transition(scene, choices))
        vids.append(fit_to_canvas(process_scene(scene_image, audio, background), canvas_size))

    if not vids:
        raise RenderFailedException("No video scenes were processed.")

    final_audio = final_video = None
    transition_clips = []
    try:
        final_video, transition_clips = compose_transitions(vids, transitions, opening_duration=choices.get("transition_duration"))

        if background:
            final_video = final_video.margin(
                top=background.image_pos_top, left=background.image_pos_left, opacity=4
            ).set_position("center")

        if sound_list:
            final_audio = concatenate_audioclips(sound_list)
            final_audio.write_audiofile(f"{video.dir_name}/output_audio.wav")

        final_video = handle_final_video(
            background, final_audio, final_video, video, subtitles
        )
        final_video_path = f"{video.dir_name}/output_video.mp4"
        # Explicit aac: moviepy defaults to libmp3lame, and Safari and QuickTime
        # silently drop an mp3 audio track inside an mp4.
        final_video.write_videofile(
            final_video_path,
            fps=24,
            threads=8,
            codec="libx264",
            audio_codec="aac",
        )

        video.output = final_video_path
        video.status = VideoStatus.COMPLETED

    finally:
        closed = set()
        for clip in sound_list + vids + subtitles + transition_clips + [final_audio, final_video]:
            if clip is None or id(clip) in closed:
                continue
            closed.add(id(clip))
            try:
                clip.close()
            except Exception as exc:
                logger.warning("Ignoring error while closing a clip: %s", exc)

    video.save()
    return video
