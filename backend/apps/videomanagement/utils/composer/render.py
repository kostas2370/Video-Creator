import logging
import math
import os
import subprocess
import tempfile
from copy import copy
from pathlib import Path

from django.conf import settings

from apps.videomanagement.exceptions import RenderFailedException
from apps.videomanagement.services.captions.alignment import align_scene_narration
from apps.videomanagement.services.videos.preview import (
    apply_transitions,
    asset_segment,
    intro_segment,
    scene_segment,
)
from apps.videomanagement.utils.frames import save_video_frame

from ...models import RENDERABLE_STATUSES, MotionStyle, VideoStatus
from ...video_formats import output_size
from ..audio_editing import narration_file, voice_tracks
from ..file_utils import check_if_image, stored_file_exists
from ..fonts import subtitles_filter
from ..motion import AMOUNTS, resolved_motion
from ..timing import media_timing
from .audio import voice_stream, write_music_envelope
from .captions import write_captions
from .effects import audio_fade_filters
from .overlays import apply_overlays

logger = logging.getLogger(__name__)
FPS = 24


class Graph:
    def __init__(self):
        self.inputs = []
        self.filters = []
        self.input_count = 0
        self.stream_count = 0

    def input(self, path, options=()):
        index = self.input_count
        self.input_count += 1
        self.inputs.extend(["-threads", "2", *options, "-i", str(Path(path).resolve())])
        return index

    def filter(self, sources, expression, outputs=1):
        labels = [f"s{self.stream_count + index}" for index in range(outputs)]
        self.stream_count += outputs
        self.filters.append(
            "".join(f"[{source}]" for source in sources)
            + expression
            + "".join(f"[{label}]" for label in labels)
        )
        return labels[0] if outputs == 1 else labels

    def run(self, directory, output, maps, encoding, duration):
        script = Path(directory, "filters.txt")
        script.write_text(";\n".join(self.filters))
        command = [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-y",
            "-loglevel",
            "error",
            "-filter_complex_threads",
            "2",
            *self.inputs,
            "-filter_complex_script",
            str(script),
        ]
        for label in maps:
            command.extend(["-map", f"[{label}]"])
        command.extend([*encoding, "-t", str(duration), str(output)])
        with Path(directory, "ffmpeg.log").open("w+b") as log:
            try:
                subprocess.run(
                    command,
                    cwd=directory,
                    stdout=subprocess.DEVNULL,
                    stderr=log,
                    check=True,
                    timeout=settings.FFMPEG_RENDER_TIMEOUT,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                log.seek(0, os.SEEK_END)
                log.seek(max(0, log.tell() - 4000))
                detail = log.read().decode("utf-8", errors="replace").strip()
                if isinstance(exc, subprocess.CalledProcessError):
                    reason = (
                        "SIGKILL (possible out-of-memory kill)"
                        if exc.returncode == -9
                        else f"exit code {exc.returncode}"
                    )
                elif isinstance(exc, subprocess.TimeoutExpired):
                    reason = f"timed out after {exc.timeout}s"
                else:
                    reason = str(exc)
                raise RenderFailedException(
                    f"FFmpeg render failed: {reason}. {detail}".strip()
                ) from exc


def audio_stream(graph, sources, duration):
    streams = []
    for path in sources:
        index = graph.input(path)
        streams.append(
            graph.filter(
                [f"{index}:a"],
                "aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS",
            )
        )
    if not streams:
        stream = graph.filter([], "anullsrc=r=44100:cl=stereo")
    elif len(streams) == 1:
        stream = streams[0]
    else:
        stream = graph.filter(
            streams, f"amix=inputs={len(streams)}:duration=longest:normalize=0"
        )
    return graph.filter(
        [stream], f"apad,atrim=duration={duration},asetpts=PTS-STARTPTS"
    )


def narration_graph(segments, choices):
    graph = Graph()
    if any(
        segment.content.voiceover or segment.content.audio_settings
        for segment in segments
    ):
        tracks = voice_tracks(segments)
        by_id = {str(segment.content.pk): segment.content for segment in segments}
        voices = [
            voice_stream(graph, narration_file(by_id[track["id"]]).path, track)
            for track in tracks
        ]
        originals = [
            audio_stream(
                graph,
                [segment.image.file.path] if segment.clip_audio else [],
                segment.duration,
            )
            for segment in segments
        ]
        original = graph.filter(originals, f"concat=n={len(originals)}:v=0:a=1")
        if voices:
            original = graph.filter(
                [original, *voices],
                f"amix=inputs={len(voices) + 1}:duration=first:normalize=0",
            )
        return graph, original
    streams = []
    for segment in segments:
        sources = []
        if (
            choices.get("narration", True)
            and segment.narration_duration
            and stored_file_exists(segment.content.file)
        ):
            sources.append(segment.content.file.path)
        if segment.clip_audio and stored_file_exists(segment.image.file):
            sources.append(segment.image.file.path)
        streams.append(audio_stream(graph, sources, segment.duration))
    return graph, graph.filter(streams, f"concat=n={len(streams)}:v=0:a=1")


def fit_filter(size):
    width, height = size
    return f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1"


def motion_filter(scene, duration, size):
    style = resolved_motion(scene)
    amount = AMOUNTS[scene.motion_intensity]
    last = max(1, math.ceil(duration * FPS) - 1)
    progress = f"min(on/{last},1)"
    zoom = "1"
    x = "iw/2-iw/zoom/2"
    y = "ih/2-ih/zoom/2"
    if style == MotionStyle.ZOOM_IN:
        zoom = f"1+{amount}*{progress}"
    elif style == MotionStyle.ZOOM_OUT:
        zoom = f"1+{amount}*(1-{progress})"
    elif style in (MotionStyle.PAN_LEFT, MotionStyle.PAN_RIGHT):
        zoom = str(1 + amount)
        direction = "-" if style == MotionStyle.PAN_RIGHT else "+"
        x += f"{direction}iw*{amount}*({progress}-0.5)/zoom"
    elif style in (MotionStyle.PAN_UP, MotionStyle.PAN_DOWN):
        zoom = str(1 + amount)
        direction = "-" if style == MotionStyle.PAN_DOWN else "+"
        y += f"{direction}ih*{amount}*({progress}-0.5)/zoom"
    width, height = size
    return f"zoompan=z='{zoom}':x='{x}':y='{y}':d={math.ceil(duration * FPS)}:s={width}x{height}:fps={FPS}"


def visual_stream(graph, segment, size):
    field = segment.image.file if segment.image else None
    if segment.kind != "scene":
        field = segment.content.file
    if not stored_file_exists(field):
        stream = graph.filter(
            [], f"color=c=black:s={size[0]}x{size[1]}:r={FPS}:d={segment.duration}"
        )
    elif segment.visual_type == "image":
        if not check_if_image(field.name):
            stream = graph.filter(
                [], f"color=c=black:s={size[0]}x{size[1]}:r={FPS}:d={segment.duration}"
            )
        else:
            if resolved_motion(segment.content) == MotionStyle.NONE:
                index = graph.input(field.path, ("-loop", "1", "-framerate", str(FPS)))
                stream = graph.filter([f"{index}:v"], fit_filter(size))
            else:
                index = graph.input(field.path)
                stream = graph.filter(
                    [f"{index}:v"], fit_filter((size[0] * 2, size[1] * 2))
                )
                stream = graph.filter(
                    [stream],
                    motion_filter(segment.content, segment.base_duration, size),
                )
    else:
        index = graph.input(
            field.path, ("-stream_loop", "-1") if segment.loop_visual else ()
        )
        stream = graph.filter(
            [f"{index}:v"], f"setpts=PTS-STARTPTS,{fit_filter(size)},fps={FPS}"
        )
    stream = graph.filter(
        [stream],
        f"trim=duration={segment.base_duration},tpad=stop_mode=clone:stop_duration={segment.duration},trim=duration={segment.duration},setpts=PTS-STARTPTS,format=yuv420p",
    )
    fades = []
    if segment.fade_in:
        fades.append(f"fade=t=in:st=0:d={segment.fade_in}")
    if segment.fade_out:
        fades.append(
            f"fade=t=out:st={segment.duration - segment.fade_out}:d={segment.fade_out}"
        )
    return graph.filter([stream], ",".join(fades)) if fades else stream


def quantized_scenes(segments):
    quantized = []
    offset = 0
    for segment in segments:
        end = offset + segment.duration
        frames = math.ceil(end * FPS) - math.ceil(offset * FPS)
        if frames:
            visual_segment = copy(segment)
            visual_segment.duration = frames / FPS
            visual_segment.base_duration = min(
                segment.base_duration, visual_segment.duration
            )
            quantized.append(visual_segment)
        offset = end
    return quantized


def render_scene_clips(segments, directory, size, opening=None):
    quantized = quantized_scenes(segments)
    previous_frame = None
    if opening and quantized and quantized[0].dissolve_in:
        previous_frame = Path(directory, "intro-ending.png")
        save_video_frame(
            opening.content.file.path,
            previous_frame,
            max(0, opening.duration - 1 / FPS),
        )
    files = []
    for index, segment in enumerate(quantized):
        graph = Graph()
        visual = visual_stream(graph, segment, size)
        if segment.dissolve_in and previous_frame:
            frame = graph.input(previous_frame, ("-loop", "1", "-framerate", str(FPS)))
            frozen = graph.filter(
                [f"{frame}:v"],
                f"trim=duration={segment.dissolve_in},setpts=PTS-STARTPTS,format=rgba,fade=t=out:st=0:d={segment.dissolve_in}:alpha=1",
            )
            visual = graph.filter(
                [visual, frozen], "overlay=eof_action=pass:repeatlast=0:format=auto"
            )
        visual = graph.filter([visual], "format=yuv420p")
        output = Path(directory, f"scene-{index}.mkv")
        graph.run(
            directory,
            output,
            [visual],
            [
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-qp",
                "0",
                "-threads",
                "2",
                "-an",
            ],
            segment.duration,
        )
        files.append((output, segment.duration))
        previous_frame = None
        if index + 1 < len(quantized) and quantized[index + 1].dissolve_in:
            previous_frame = Path(directory, "outgoing.png")
            save_video_frame(
                output, previous_frame, max(0, segment.duration - 1 / FPS - 0.000001)
            )
    manifest = Path(directory, "scenes.ffconcat")
    manifest.write_text(
        "ffconcat version 1.0\n"
        + "".join(
            f"file '{path.name}'\nduration {duration}\n" for path, duration in files
        )
    )
    return manifest


def avatar_layer(graph, video, stream, duration):
    if not video.avatar:
        return stream
    path = Path(video.dir_name, "output_avatar.mp4").resolve()
    if not path.exists():
        # SadTalker is an optional, heavyweight dependency used only for avatar renders.
        from .avatar import create_avatar_video

        generated = create_avatar_video(video.avatar, video.dir_name)
        if not generated:
            logger.warning("Rendering video %s without unavailable avatar", video.pk)
            return stream
        path = Path(generated)
    avatar_duration = media_timing(path).get("duration")
    if not avatar_duration:
        raise RenderFailedException("Avatar timing is unavailable.")
    index = graph.input(path)
    fade = min(0.5, avatar_duration / 2)
    avatar = graph.filter(
        [f"{index}:v"],
        f"setpts=PTS-STARTPTS,scale=trunc(iw*1.5/2)*2:trunc(ih*1.5/2)*2,format=rgba,fade=t=in:st=0:d={fade}:alpha=1,fade=t=out:st={avatar_duration - fade}:d={fade}:alpha=1",
    )
    horizontal, vertical = (
        (video.settings or {}).get("avatar_position", "right,top").split(",")
    )
    x = {"left": "0", "center": "(W-w)/2", "right": "W-w"}[horizontal]
    y = {"top": "0", "center": "(H-h)/2", "bottom": "H-h"}[vertical]
    return graph.filter(
        [stream, avatar],
        f"overlay=x={x}:y={y}:eof_action=pass:repeatlast=0,trim=duration={duration}",
    )


def final_graph(
    video,
    segments,
    duration,
    narration_path,
    directory,
    size,
    scene_manifest,
    opening=None,
):
    graph = Graph()
    scene_input = graph.input(scene_manifest, ("-f", "concat", "-safe", "1"))
    visual = graph.filter([f"{scene_input}:v"], "setpts=PTS-STARTPTS")
    visual = avatar_layer(graph, video, visual, duration)
    visual = apply_overlays(graph, visual, segments, size, directory)
    audio = audio_stream(graph, [narration_path], duration)
    if video.music:
        index = graph.input(video.music.file.path, ("-stream_loop", "-1"))
        choices = video.settings or {}
        filters = [
            "aresample=44100",
            "aformat=sample_fmts=fltp:channel_layouts=stereo",
            f"atrim=duration={duration}",
            "asetpts=PTS-STARTPTS",
        ]
        if choices.get("music_ducking"):
            speech = [
                interval
                for track in voice_tracks(segments)
                for interval in track["speech"]
            ]
            envelope_path = Path(directory, "music-envelope.f32")
            write_music_envelope(envelope_path, duration, choices, speech)
            control = graph.input(
                envelope_path, ("-f", "f32le", "-ar", "44100", "-ac", "2")
            )
            envelope = graph.filter(
                [f"{control}:a"], "aformat=sample_fmts=fltp:channel_layouts=stereo"
            )
            music = graph.filter([f"{index}:a"], ",".join(filters))
            music = graph.filter([music, envelope], "amultiply")
        else:
            fade = min(4, duration * 0.1)
            filters.append(f"volume={choices.get('music_volume', 0.07)}")
            filters.extend(
                audio_fade_filters(
                    duration,
                    fade_in=choices.get("music_fade_in", fade),
                    fade_out=choices.get("music_fade_out", fade),
                )
            )
            music = graph.filter([f"{index}:a"], ",".join(filters))
        audio = graph.filter([audio, music], "amix=inputs=2:duration=first:normalize=0")
    if (video.settings or {}).get("subtitles", False):
        write_captions(Path(directory, "captions.ass"), segments, size)
        visual = graph.filter([visual], subtitles_filter("captions.ass", directory))
    visuals, audios = [], []
    total = duration
    if opening:
        visuals.append(visual_stream(graph, opening, size))
        audios.append(
            audio_stream(
                graph,
                [video.intro.file.path] if opening.clip_audio else [],
                opening.duration,
            )
        )
        total += opening.duration
    visuals.append(visual)
    audios.append(audio)
    if video.outro:
        closing = asset_segment(video.outro, "outro", 0)
        visuals.append(visual_stream(graph, closing, size))
        audios.append(
            audio_stream(
                graph,
                [video.outro.file.path] if closing.clip_audio else [],
                closing.duration,
            )
        )
        total += closing.duration
    visual = graph.filter(visuals, f"concat=n={len(visuals)}:v=1:a=0")
    audio = graph.filter(audios, f"concat=n={len(audios)}:v=0:a=1")
    visual = graph.filter([visual], f"fps={FPS},format=yuv420p")
    return graph, visual, audio, total


def make_video(video):
    if video.status not in RENDERABLE_STATUSES:
        raise RenderFailedException("Video is not in a renderable state.")
    choices = video.settings or {}
    segments, elapsed = [], 0
    for index, scene in enumerate(video.scenes.with_media(), 1):
        if choices.get("subtitles"):
            align_scene_narration(scene)
        segment = scene_segment(scene, index, elapsed, choices)
        segments.append(segment)
        elapsed += segment.duration
    if not segments:
        raise RenderFailedException("No video scenes were processed.")
    opening = intro_segment(video) if video.intro else None
    apply_transitions(segments, choices, opening)
    video.status = VideoStatus.RENDERING
    video.save(update_fields=["status", "updated_at"])
    destination = Path(video.dir_name).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="ffmpeg-render-", dir=destination
    ) as directory:
        graph, audio = narration_graph(segments, choices)
        narration = Path(directory, "narration.wav")
        graph.run(
            directory,
            narration,
            [audio],
            ["-c:a", "pcm_s16le", "-ar", "44100"],
            elapsed,
        )
        os.replace(narration, destination / "output_audio.wav")
        size = output_size(choices.get("video_format"))
        manifest = render_scene_clips(segments, directory, size, opening)
        graph, visual, audio, total = final_graph(
            video,
            segments,
            elapsed,
            destination / "output_audio.wav",
            directory,
            size,
            manifest,
            opening,
        )
        output = Path(directory, "output.mp4")
        graph.run(
            directory,
            output,
            [visual, audio],
            [
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-threads",
                "8",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
            ],
            total,
        )
        os.replace(output, destination / "output_video.mp4")
    video.output = os.path.relpath(
        destination / "output_video.mp4", settings.MEDIA_ROOT
    )
    video.status = VideoStatus.COMPLETED
    video.thumbnail = ""
    video.save(update_fields=["output", "status", "updated_at", "thumbnail"])
    return video
