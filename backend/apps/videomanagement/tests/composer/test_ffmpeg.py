
import json
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

import numpy as np
from django.test import TestCase, override_settings
from PIL import Image

from apps.videomanagement.exceptions import RenderFailedException
from apps.videomanagement.utils.frames import still_from_video

from ...baker_recipes import (
    avatar,
    intro,
    music,
    outro,
    scene,
    scene_image,
    video,
)
from ...serializers.overlays import OverlaySerializer
from ...utils.composer.render import Graph, make_video


@skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools required")
class FFmpegRenderTests(TestCase):
    def test_tiktok_caption_highlight_moves_to_the_next_word_in_export(self):
        Image.new("RGB", (160, 90), "black").save(self.root / "still.png")
        self.row.settings.update(subtitles=True, platform="TIKTOK")
        self.row.save()
        self.add_still(text="One two")
        make_video(self.row)

        def yellow_x(timestamp):
            frame = self.frame(timestamp)
            mask = (frame[:, :, 0] > 120) & (frame[:, :, 1] > 120) & (frame[:, :, 2] < 110)
            ys, xs = np.where(mask)
            self.assertGreater(len(xs), 2)
            self.assertTrue((ys > 55).all())
            return xs.mean()

        self.assertLess(yellow_x(0.08), yellow_x(0.38))

    def test_bundled_font_is_loaded_for_captions_and_overlays(self):
        Image.new("RGB", (160, 90), "black").save(self.root / "still.png")
        item = self.add_still(text="Caption")
        run = subprocess.run
        logs = []

        def capture_font_selection(command, *args, **kwargs):
            command = list(command)
            final_render = command[0] == "ffmpeg" and "-filter_complex_script" in command
            if final_render:
                command[command.index("-loglevel") + 1] = "info"
            result = run(command, *args, **kwargs)
            if final_render:
                log = kwargs["stderr"]
                log.seek(0)
                logs.append(log.read().decode("utf-8", errors="replace"))
            return result

        for font, face in (("Poppins", "Poppins-Bold"), ("Lato", "Lato-Bold"), ("Bebas Neue", "BebasNeue-Regular")):
            with self.subTest(font=font):
                logs.clear()
                self.row.settings.update(subtitles=True, caption_style="CUSTOM", caption_config={"font": font})
                self.row.save()
                overlay = OverlaySerializer(data={"kind": "title", "text": "TITLE", "font": font, "position": "top-center"})
                overlay.is_valid(raise_exception=True)
                item.overlays = [overlay.validated_data]
                item.save(update_fields=["overlays"])
                with patch("apps.videomanagement.utils.composer.render.subprocess.run", side_effect=capture_font_selection):
                    make_video(self.row)
                selected = re.findall(r"fontselect: .* -> .*" + re.escape(face), "\n".join(logs))
                # Captions and overlays use separate libass filters: both must load this face.
                self.assertGreaterEqual(len(selected), 2, "\n".join(logs))

    def test_overlays_follow_timing_and_logo_placement_in_export(self):

        Image.new("RGB", (160, 90), "black").save(self.root / "still.png")
        Image.new("RGBA", (32, 32), "red").save(self.root / "logo.png")
        settings = OverlaySerializer(data=[
            {"kind": "title", "text": "HELLO", "start": 0.1, "end": 0.3, "size": 8, "background": False},
            {"kind": "watermark", "logo": True, "position": "top-left", "start": 0.1, "end": 0.3, "width": 20},
        ], many=True)
        settings.is_valid(raise_exception=True)
        self.add_still(overlays=settings.validated_data, overlay_logo="logo.png")
        make_video(self.row)
        before, visible, after = self.frame(0), self.frame(0.2), self.frame(0.4)
        self.assertLess(before.max(), 15)
        self.assertLess(after.max(), 15)
        self.assertGreater(visible[6:30, 10:35, 0].mean(), 200)
        self.assertGreater((visible[30:85, :, :].max(axis=2) > 150).sum(), 10)

    def test_overlay_offsets_include_intro_and_previous_scene_pause(self):

        Image.new("RGB", (160, 90), "black").save(self.root / "still.png")
        Image.new("RGBA", (32, 32), "red").save(self.root / "logo.png")
        self.row.intro = intro.make(file="intro.mp4")
        self.row.save()
        self.add_still(pause_after=0.25, transition_after="CUT")
        settings = OverlaySerializer(data=[
            {"kind": "watermark", "logo": True, "position": "bottom-right", "start": 0.1, "end": 0.3, "width": 20},
        ], many=True)
        settings.is_valid(raise_exception=True)
        self.add_still(overlays=settings.validated_data, overlay_logo="logo.png")
        make_video(self.row)
        self.assertLess(self.frame(0.9).max(), 15)
        self.assertGreater(self.frame(1.2)[55:80, 125:150, 0].mean(), 200)
        self.assertLess(self.frame(1.4).max(), 15)

    def test_wide_overlay_text_stays_inside_the_export_frame(self):
        Image.new("RGB", (160, 90), "black").save(self.root / "still.png")
        overlay = OverlaySerializer(data={
            "kind": "title", "text": "W" * 200, "font": "Poppins",
            "size": 8, "position": "middle-center", "background": False,
        })
        overlay.is_valid(raise_exception=True)
        self.add_still(overlays=[overlay.validated_data])
        make_video(self.row)
        frame = self.frame(0.1)
        ys, xs = np.where(frame.max(axis=2) > 100)
        self.assertGreater(len(xs), 10)
        self.assertGreater(xs.min(), 3)
        self.assertLess(xs.max(), 156)
        self.assertGreater(ys.min(), 2)
        self.assertLess(ys.max(), 87)

    def test_intro_cut_fade_and_dissolve_are_present_in_the_export(self):
        Image.new("RGB", (160, 90), "red").save(self.root / "still.png")
        self.add_still(transition_after="CUT")
        self.row.intro = intro.make(file="intro.mp4")
        self.row.settings["intro_transition_duration"] = 0.125
        for style in ("CUT", "FADE", "DISSOLVE"):
            with self.subTest(style=style):
                self.row.settings["intro_transition"] = style
                self.row.save()
                make_video(self.row)
                boundary = self.frame(0.25).mean(axis=(0, 1))
                later = self.frame(0.5).mean(axis=(0, 1))
                self.assertGreater(later[0], 220)
                self.assertLess(later[2], 20)
                self.assertAlmostEqual(float(self.metadata()["format"]["duration"]), 0.75, delta=0.05)
                if style == "CUT":
                    self.assertGreater(boundary[0], 220)
                    self.assertLess(boundary[2], 20)
                elif style == "FADE":
                    self.assertLess(boundary.max(), 20)
                else:
                    self.assertGreater(boundary[2], 220)
                    self.assertLess(boundary[0], 20)

    def setUp(self):
        # Rendering fixtures use synthetic tones; speech providers stay mocked.
        self.enterContext(patch("apps.videomanagement.utils.composer.render.align_scene_narration"))
        self.directory = tempfile.TemporaryDirectory(prefix="ffmpeg-tests-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        override = override_settings(
            MEDIA_ROOT=str(self.root), FFMPEG_RENDER_TIMEOUT=60
        )
        override.enable()
        self.addCleanup(override.disable)
        patcher = patch(
            "apps.videomanagement.utils.composer.render.output_size",
            return_value=(160, 90),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        pixels = np.full((90, 160, 3), 80, dtype=np.uint8)
        pixels[:, :, 0] = np.arange(160) + 30
        Image.fromarray(pixels).save(self.root / "still.png")
        with wave.open(str(self.root / "speech.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(44100)
            t = np.arange(22050) / 44100
            wav.writeframes(
                (np.sin(2 * np.pi * 440 * t) * 5000).astype("int16").tobytes()
            )
        self.create_clip("clip.mp4", "green", 0.3)
        self.create_clip("intro.mp4", "blue", 0.25)
        self.create_clip("outro.mp4", "red", 0.25)
        self.row = video.make(
            status="READY",
            dir_name=str(self.root / "output"),
            settings={
                "narration": True,
                "subtitles": False,
                "transition_default": "CUT",
            },
        )

    def create_clip(self, name, color, duration):
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c={color}:s=160x90:r=24:d={duration}",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=880:sample_rate=44100",
                "-t",
                str(duration),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(self.root / name),
            ],
            check=True,
            capture_output=True,
        )

    def add_still(self, **kwargs):
        row = scene.make(video=self.row, file="speech.wav", is_last=False, **kwargs)
        scene_image.make(scene=row, file="still.png", with_audio=False)
        return row

    def metadata(self):
        return json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_format",
                    "-show_streams",
                    "-of",
                    "json",
                    self.row.output.path,
                ]
            )
        )

    def frame(self, time):
        raw = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                str(time),
                "-i",
                self.row.output.path,
                "-frames:v",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "pipe:1",
            ]
        )
        return np.frombuffer(raw, dtype=np.uint8).reshape((90, 160, 3))

    def test_native_motion_and_pause_produce_seekable_h264_aac(self):
        self.row.thumbnail = "media/thumbnails/previous.jpg"
        self.row.save(update_fields=["thumbnail"])
        self.add_still(
            motion_style="PAN_RIGHT", motion_intensity="STRONG", pause_after=0.25
        )
        make_video(self.row)
        data = self.metadata()
        self.assertEqual(self.row.status, "COMPLETED")
        self.row.refresh_from_db()
        self.assertFalse(self.row.thumbnail)
        self.assertEqual(
            [(s["codec_type"], s["codec_name"]) for s in data["streams"]],
            [("video", "h264"), ("audio", "aac")],
        )
        self.assertAlmostEqual(float(data["format"]["duration"]), 0.75, delta=0.05)
        self.assertGreater(
            abs(
                float(self.frame(0.1)[:, 80, 0].mean())
                - float(self.frame(0.45)[:, 80, 0].mean())
            ),
            3,
        )
        np.testing.assert_allclose(self.frame(0.55), self.frame(0.65), atol=3)

    def test_dissolve_keeps_narration_duration_and_scene_order(self):
        self.add_still(transition_after="DISSOLVE", transition_duration=0.2)
        second = scene.make(
            video=self.row, file="speech.wav", is_last=False, transition_after="CUT"
        )
        scene_image.make(scene=second, file="clip.mp4", with_audio=True)
        make_video(self.row)
        self.assertAlmostEqual(
            float(self.metadata()["format"]["duration"]), 1, delta=0.05
        )
        self.assertGreater(
            self.frame(0.8)[:, :, 1].mean(), self.frame(0.8)[:, :, 0].mean()
        )
        self.assertGreater(
            self.frame(0.52)[:, :, 0].mean(), self.frame(0.75)[:, :, 0].mean()
        )

    def test_assets_music_captions_and_cached_avatar_render_natively(self):
        self.add_still(
            text="Hello {world} \\ test. Καλημέρα!",
            transition_after="FADE",
            transition_duration=0.1,
        )
        self.row.settings.update(subtitles=True, transition_default="FADE")
        self.row.intro = intro.make(file="intro.mp4")
        self.row.outro = outro.make(file="outro.mp4")
        self.row.music = music.make(file="speech.wav")
        self.row.avatar = avatar.make()
        Path(self.row.dir_name).mkdir()
        shutil.copy(
            self.root / "clip.mp4", Path(self.row.dir_name, "output_avatar.mp4")
        )
        self.row.save()
        make_video(self.row)
        self.assertAlmostEqual(
            float(self.metadata()["format"]["duration"]), 1, delta=0.05
        )
        self.assertGreater(self.frame(0.1)[:, :, 2].mean(), 200)
        self.assertGreater(self.frame(0.9)[:, :, 0].mean(), 200)

    def test_silent_video_retains_its_length_and_optional_soundtrack(self):
        self.row.settings = {"narration": False, "transition_default": "CUT"}
        self.row.save()
        row = scene.make(video=self.row, is_last=False, pause_after=0.25)
        scene_image.make(scene=row, file="clip.mp4", with_audio=True)
        make_video(self.row)
        self.assertAlmostEqual(
            float(self.metadata()["format"]["duration"]), 0.55, delta=0.05
        )

    def test_failure_preserves_previous_output_and_cleans_temporary_files(self):
        self.row.thumbnail = "media/thumbnails/previous.jpg"
        self.row.save(update_fields=["thumbnail"])
        self.add_still()
        output = Path(self.row.dir_name)
        output.mkdir()
        (output / "output_video.mp4").write_bytes(b"previous render")
        with patch(
            "apps.videomanagement.utils.composer.render.subprocess.run",
            side_effect=subprocess.TimeoutExpired("ffmpeg", 60),
        ):
            with self.assertRaises(RenderFailedException):
                make_video(self.row)
        self.assertEqual((output / "output_video.mp4").read_bytes(), b"previous render")
        self.assertEqual(list(output.glob("ffmpeg-render-*")), [])
        self.row.refresh_from_db()
        self.assertEqual(self.row.thumbnail.name, "media/thumbnails/previous.jpg")

    def test_ending_holds_and_pauses_are_silent_after_narration(self):
        row = self.add_still(pause_after=0.25)
        row.is_last = True
        row.save()
        make_video(self.row)
        raw = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                self.row.output.path,
                "-map",
                "0:a",
                "-f",
                "f32le",
                "-ac",
                "1",
                "-ar",
                "44100",
                "pipe:1",
            ]
        )
        audio = np.frombuffer(raw, dtype=np.float32)
        self.assertGreater(np.abs(audio[4410:17640]).mean(), 0.01)
        self.assertLess(np.abs(audio[33075:44100]).mean(), 0.001)
        self.assertGreater(float(self.metadata()["format"]["duration"]), 2.5)

    def test_portrait_and_square_exports_keep_requested_dimensions(self):
        self.add_still()
        for size in ((90, 160), (90, 90)):
            self.row.status = "READY"
            with patch(
                "apps.videomanagement.utils.composer.render.output_size",
                return_value=size,
            ):
                make_video(self.row)
            stream = self.metadata()["streams"][0]
            self.assertEqual((stream["width"], stream["height"]), size)

    def test_fractional_scene_durations_do_not_accumulate_visual_drift(self):
        for _ in range(9):
            self.add_still(pause_after=0.13)
        final = self.add_still(pause_after=0.13)
        Image.new("RGB", (160, 90), "red").save(self.root / "red.png")
        visual = final.scene_images.get()
        visual.file = "red.png"
        visual.save()
        make_video(self.row)
        self.assertGreater(self.frame(5.8)[:, :, 0].mean(), 200)
        self.assertAlmostEqual(
            float(self.metadata()["format"]["duration"]), 6.3, delta=0.05
        )
        self.assertEqual(self.row.output.name, "output/output_video.mp4")

    def test_continuation_frames_are_decoded_with_native_ffmpeg(self):

        anchor = still_from_video(
            str(self.root / "clip.mp4"), str(self.root) + "/", end_time=0.2
        )
        self.assertIsNotNone(anchor)
        with Image.open(anchor) as image:
            pixels = np.asarray(image)
        self.assertEqual(pixels.shape, (90, 160, 3))
        self.assertGreater(pixels[:, :, 1].mean(), pixels[:, :, 0].mean())

    def test_many_dissolves_use_only_one_scene_and_one_held_frame_at_a_time(self):

        for _ in range(10):
            self.add_still(
                motion_style="PAN_RIGHT",
                transition_after="DISSOLVE",
                transition_duration=0.1,
            )
        original = Graph.run
        scene_inputs = []

        def record(graph, directory, output, *args):
            if Path(output).name.startswith("scene-"):
                scene_inputs.append(graph.input_count)
            return original(graph, directory, output, *args)

        with patch.object(Graph, "run", record):
            make_video(self.row)
        self.assertEqual(len(scene_inputs), 10)
        self.assertLessEqual(max(scene_inputs), 2)
        self.assertAlmostEqual(
            float(self.metadata()["format"]["duration"]), 5, delta=0.05
        )

    def test_sigkill_with_empty_stderr_reports_a_possible_memory_kill(self):

        graph = Graph()
        stream = graph.filter([], "color=c=black:s=160x90:d=1")
        with patch(
            "apps.videomanagement.utils.composer.render.subprocess.run",
            side_effect=subprocess.CalledProcessError(-9, "ffmpeg"),
        ):
            with self.assertRaisesRegex(
                RenderFailedException, "SIGKILL.*out-of-memory"
            ):
                graph.run(self.root, self.root / "failed.mp4", [stream], [], 1)
