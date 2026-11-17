"""Original MP3 audio becomes independent editable scene clips, without TTS."""

import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.common.media import run_ffmpeg
from apps.videomanagement.models import Video
from apps.videomanagement.services.videos.audio import (
    prepare_audio_scenes,
    transcribe_source_audio,
)
from apps.videomanagement.services.videos.generation import generate_video
from apps.videomanagement.services.videos.jobs import approve_script
from apps.videomanagement.tests.api.base import ApiTestCase

WORDS = [
    {"text": "Hello", "start": 0.3, "end": 0.6},
    {"text": "there.", "start": 0.7, "end": 1.0},
    {"text": "Goodbye", "start": 2.3, "end": 2.6},
    {"text": "now.", "start": 3.0, "end": 3.4},
]
SCRIPT = {
    "title": "Recorded greeting",
    "visual_continuity": "",
    "scenes": [
        {
            "scene": "Hello",
            "sentences": [
                {"sentence": "Hello there.", "image_description": "A sunrise"}
            ],
        },
        {
            "scene": "Goodbye",
            "sentences": [
                {"sentence": "Goodbye now.", "image_description": "A sunset"}
            ],
        },
    ],
}


class AudioVideoTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        setting = override_settings(MEDIA_ROOT=self.directory.name)
        setting.enable()
        self.addCleanup(setting.disable)
        self.path = Path(self.directory.name, "original.mp3")
        run_ffmpeg(
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=4",
                "-c:a",
                "libmp3lame",
                str(self.path),
            ]
        )

    def upload(self):
        return SimpleUploadedFile(
            "recording.mp3", self.path.read_bytes(), content_type="audio/mpeg"
        )

    def queue(self, **extra):
        with patch("apps.videomanagement.tasks.generate_video_task.delay") as delay:
            response = self.client.post(
                reverse("generate-audio-video"),
                {"source_audio": self.upload(), **extra},
                format="multipart",
            )
        self.assertEqual(response.status_code, 202, response.data)
        return Video.objects.get(pk=response.data["video"]["id"]), delay

    def test_upload_is_persisted_before_queueing_without_voice_or_file_in_task(self):
        project, delay = self.queue(
            voice_id="caller-voice",
            avatar_selection="caller-avatar",
            source_text="Invent narration",
        )
        self.assertTrue(Path(project.source_audio.path).is_file())
        self.assertAlmostEqual(project.source_audio_duration, 4, delta=0.1)
        self.assertEqual(project.settings["creation_mode"], "AUDIO")
        self.assertNotIn("source_audio", delay.call_args.kwargs)
        self.assertNotIn("source_text", delay.call_args.kwargs)
        self.assertNotIn("source_audio_duration", delay.call_args.kwargs)
        self.assertIsNone(delay.call_args.kwargs["voice_id"])
        self.assertEqual(delay.call_args.kwargs["avatar_selection"], "")
        self.assertTrue(delay.call_args.kwargs["review_script"])

    def test_review_then_generation_splits_original_audio_without_synthesis(self):
        project, delay = self.queue()
        params = {
            key: value
            for key, value in delay.call_args.kwargs.items()
            if key not in ("video_id", "operation_id")
        }
        with (
            patch(
                "apps.videomanagement.services.videos.audio.transcribe_audio",
                return_value=WORDS,
            ) as transcribe,
            patch(
                "apps.videomanagement.services.videos.generation.get_reply",
                return_value=SCRIPT,
            ),
            patch(
                "apps.videomanagement.services.videos.generation.generate_directory",
                return_value=self.directory.name,
            ),
            patch(
                "apps.videomanagement.services.videos.generation.create_image_scenes"
            ) as visuals,
            patch(
                "apps.videomanagement.services.videos.generation.make_scenes_speech"
            ) as speech,
            patch(
                "apps.videomanagement.services.scenes.narration.narrate_scene"
            ) as tts,
            patch(
                "apps.videomanagement.models.VoiceModel.select_voice"
            ) as select_voice,
            patch("apps.videomanagement.services.videos.generation.download_music"),
        ):
            generate_video(project, **params)
            self.assertEqual(project.status, "REVIEW")
            self.assertEqual(project.scenes.count(), 0)
            visuals.assert_not_called()
            with patch(
                "apps.videomanagement.tasks.generate_video_task.delay"
            ) as approved:
                project = approve_script(project, SCRIPT)
            params = {
                key: value
                for key, value in approved.call_args.kwargs.items()
                if key not in ("video_id", "operation_id")
            }
            generate_video(project, **params)
            self.assertEqual(project.status, "READY")
            clips = list(project.scenes.all())
            self.assertEqual(len(clips), 2)
            self.assertNotEqual(clips[0].file.name, clips[1].file.name)
            durations, pcm = [], []
            for clip in clips:
                with wave.open(clip.file.path) as audio:
                    durations.append(audio.getnframes() / audio.getframerate())
                    pcm.append(audio.readframes(audio.getnframes()))
                self.assertTrue(clip.caption_alignment["source"])
            decoded = Path(self.directory.name, "decoded-original.wav")
            run_ffmpeg(
                ["-i", project.source_audio.path, "-c:a", "pcm_s16le", str(decoded)]
            )
            with wave.open(str(decoded)) as original:
                self.assertEqual(
                    b"".join(pcm), original.readframes(original.getnframes())
                )
            self.assertAlmostEqual(
                sum(durations), project.source_audio_duration, delta=0.02
            )
            self.assertAlmostEqual(durations[0], 1.65, delta=0.02)
            self.assertAlmostEqual(
                clips[1].caption_alignment["words"][0]["start"], 0.65
            )
            transcribe.assert_called_once()
            speech.assert_not_called()
            tts.assert_not_called()
            select_voice.assert_not_called()
            old_files = [clip.file.name for clip in clips]
            prepare_audio_scenes(project)
            self.assertEqual(
                [clip.file.name for clip in project.scenes.all()], old_files
            )

    def test_upload_validation_and_queue_failure_do_not_leave_orphaned_recordings(self):
        for name, content in (("bad.txt", b"wrong format"), ("fake.mp3", b"not audio")):
            with patch("apps.videomanagement.tasks.generate_video_task.delay") as delay:
                response = self.client.post(
                    reverse("generate-audio-video"),
                    {"source_audio": SimpleUploadedFile(name, content)},
                )
            self.assertEqual(response.status_code, 400)
            delay.assert_not_called()
        with patch(
            "apps.videomanagement.tasks.generate_video_task.delay",
            side_effect=RuntimeError("offline"),
        ):
            response = self.client.post(
                reverse("generate-audio-video"), {"source_audio": self.upload()}
            )
        self.assertEqual(response.status_code, 503)
        project = Video.objects.get()
        self.assertFalse(project.source_audio)
        self.assertEqual(project.status, "FAILED")
        self.assertFalse(
            list(Path(self.directory.name, "media", "narration").rglob("*.mp3"))
        )

    def test_silent_transcription_stops_before_generating_media(self):
        project, _ = self.queue()
        with patch(
            "apps.videomanagement.services.videos.audio.transcribe_audio",
            return_value=[],
        ):
            from rest_framework.exceptions import ValidationError

            with self.assertRaises(ValidationError):
                transcribe_source_audio(project)
        self.assertFalse(project.scenes.exists())

    def test_source_recording_is_private(self):
        from django.http import Http404
        from apps.usermanagement.baker_recipes import user
        from apps.videomanagement.protected_media import authorized_file

        project, _ = self.queue()
        self.assertEqual(
            authorized_file(self.user, project.source_audio.name).name,
            project.source_audio.name,
        )
        with self.assertRaises(Http404):
            authorized_file(user.make(), project.source_audio.name)

    def test_approval_rejects_changed_recorded_words(self):
        project, _ = self.queue()
        project.source_audio_words = WORDS
        project.status = "REVIEW"
        project.gpt_answer = SCRIPT
        project.save()
        from rest_framework.exceptions import ValidationError

        with (
            self.assertRaises(ValidationError),
            patch("apps.videomanagement.tasks.generate_video_task.delay") as delay,
        ):
            approve_script(
                project,
                {
                    **SCRIPT,
                    "scenes": [
                        {
                            "scene": "changed",
                            "sentences": [
                                {
                                    "sentence": "Invented narration",
                                    "image_description": "A cat",
                                }
                            ],
                        }
                    ],
                },
            )
        delay.assert_not_called()

    def test_editor_audio_toggle_and_text_edits_never_synthesize_narration(self):
        from apps.videomanagement.baker_recipes import scene
        from apps.videomanagement.services.scenes.generation import update_scene
        from apps.videomanagement.services.scenes.narration import narrate_scene
        from apps.videomanagement.services.videos.settings import video_update
        from rest_framework.exceptions import ValidationError

        project, _ = self.queue()
        project.status = "READY"
        project.settings = {**project.settings, "narration": False}
        project.save()
        clip = scene.make(video=project, text="Original words")
        with patch(
            "apps.videomanagement.tasks.regenerate_narration_task.delay"
        ) as regenerate:
            video_update(project, narration=True)
        regenerate.assert_not_called()
        with patch("apps.videomanagement.services.scenes.narration.ApiSyn") as tts:
            update_scene("Corrected caption words", clip)
            narrate_scene(clip, object(), "unused")
        tts.assert_not_called()
        with self.assertRaises(ValidationError):
            video_update(project, voice_id="another-voice")
