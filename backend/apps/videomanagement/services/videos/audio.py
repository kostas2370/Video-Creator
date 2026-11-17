"""Keep uploaded narration, split it by timestamp, and reuse ordinary scene visuals."""

import tempfile
import wave
from pathlib import Path

from django.core.files import File
from rest_framework.exceptions import ValidationError

from apps.common.media import run_ffmpeg
from apps.usage.services import video_usage
from apps.videomanagement.services.captions.alignment import narration_identity
from apps.videomanagement.services.captions.transcription import transcribe_audio
from apps.videomanagement.utils.file_utils import stored_file_exists
from apps.videomanagement.utils.storyboard import script_lines


def transcribe_source_audio(video):
    if not video.source_audio_words:
        with (
            tempfile.TemporaryDirectory(prefix="audio-storyboard-") as directory,
            video_usage(video),
        ):
            # MP3 container duration includes encoder padding. Measure decoded samples
            # so scene clips cover the recording exactly, without synthetic padding.
            decoded = Path(directory, "original.wav")
            run_ffmpeg(
                [
                    "-i",
                    video.source_audio.path,
                    "-map",
                    "0:a:0",
                    "-vn",
                    "-c:a",
                    "pcm_s16le",
                    str(decoded),
                ],
                timeout=120,
            )
            with wave.open(str(decoded)) as audio:
                video.source_audio_duration = audio.getnframes() / audio.getframerate()
            words = transcribe_audio(
                decoded, video.created_by, video.source_audio_duration, directory
            )
        if not words:
            raise ValidationError(
                "No speech was detected in this recording. Choose a recording with clear spoken narration."
            )
        video.source_audio_words = words
        video.save(update_fields=["source_audio_words", "source_audio_duration"])
    text = " ".join(word["text"] for word in video.source_audio_words)
    if len(text) > 20000:
        raise ValidationError(
            "This recording has too much speech. Choose a shorter recording (up to 20,000 transcript characters)."
        )
    return text


def validate_audio_storyboard(video, storyboard):
    source = " ".join(word["text"] for word in video.source_audio_words)
    actual = " ".join(line.narration for line in script_lines(storyboard))
    if not source.strip() or actual.split() != source.split():
        raise ValidationError(
            "Keep the recorded words in their original order. You can change scene breaks and visuals; the recording supplies the narration."
        )


def audio_scene_ranges(video):
    validate_audio_storyboard(video, video.gpt_answer)
    words = video.source_audio_words
    lines = list(script_lines(video.gpt_answer))
    offset, start = 0, 0.0
    ranges = []
    for index, line in enumerate(lines):
        count = len(line.narration.split())
        stop = offset + count
        end = (
            video.source_audio_duration
            if index == len(lines) - 1
            else (words[stop - 1]["end"] + words[stop]["start"]) / 2
        )
        if end <= start:
            raise ValidationError(
                "The transcript timing could not be split into playable scenes. Try another recording."
            )
        captions = [
            {
                "text": word["text"],
                "start": max(0, word["start"] - start),
                "end": min(end, word["end"]) - start,
            }
            for word in words[offset:stop]
        ]
        ranges.append((start, end, captions))
        offset, start = stop, end
    return ranges


def prepare_audio_scenes(video):
    # Local import avoids the narration/alignment import cycle. This never calls TTS.
    from apps.videomanagement.services.scenes.narration import ensure_scene_rows

    ranges = audio_scene_ranges(video)
    _, rows = ensure_scene_rows(video)
    pending = [
        (index, bounds)
        for index, bounds in enumerate(ranges)
        if not stored_file_exists(rows[index].file)
    ]
    if not pending:
        return
    # Decode once, then partition native PCM samples. Rounded frame boundaries are
    # shared by neighboring clips, avoiding missing or duplicated samples at cuts.
    with tempfile.TemporaryDirectory(prefix="scene-narration-") as directory:
        decoded = Path(directory, "original.wav")
        run_ffmpeg(
            [
                "-i",
                video.source_audio.path,
                "-map",
                "0:a:0",
                "-vn",
                "-c:a",
                "pcm_s16le",
                str(decoded),
            ],
            timeout=120,
        )
        with wave.open(str(decoded)) as original:
            rate = original.getframerate()
            for index, (start, end, captions) in pending:
                scene = rows[index]
                first = round(start * rate)
                last = min(original.getnframes(), round(end * rate))
                original.setpos(first)
                output = Path(directory, "scene.wav")
                with wave.open(str(output), "wb") as clip:
                    clip.setnchannels(original.getnchannels())
                    clip.setsampwidth(original.getsampwidth())
                    clip.setframerate(rate)
                    remaining = last - first
                    while remaining:
                        count = min(65536, remaining)
                        clip.writeframesraw(original.readframes(count))
                        remaining -= count
                with output.open("rb") as audio:
                    scene.file.save(f"{scene.pk}-imported.wav", File(audio), save=False)
                # Caption times follow the actual sample boundary of this clip.
                shift = start - first / rate
                scene.caption_alignment = {
                    "source": narration_identity(scene),
                    "words": [
                        {
                            **word,
                            "start": max(0, word["start"] + shift),
                            "end": min((last - first) / rate, word["end"] + shift),
                        }
                        for word in captions
                    ],
                }
                scene.save(update_fields=["file", "caption_alignment"])
