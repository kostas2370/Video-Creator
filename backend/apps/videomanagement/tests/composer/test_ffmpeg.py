
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
from django.conf import settings
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
from ...utils.composer.render import Graph, make_video, render_scene_clip


@skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools required")
class FFmpegRenderTests(TestCase):
    def test_photo_presets_export_with_text_particles_and_frozen_pause(self):
        serializer = OverlaySerializer(data={"kind": "title", "text": "Look!", "size": 8})
        serializer.is_valid(raise_exception=True)
        scene = self.add_still(motion_style="NONE", pause_after=.25, overlays=[serializer.validated_data])
        self.row.settings.update(transition_default="CUT", export_fps=30)
        self.row.save()
        for preset in ("PLAYFUL", "DRAMATIC", "CALM", "EXPLAINER"):
            with self.subTest(preset=preset):
                scene.animation_preset = preset
                scene.save()
                make_video(self.row)
                self.assertEqual(self.metadata()["streams"][0]["r_frame_rate"], "30/1")
                self.assertGreater(np.abs(self.frame(.03).astype(float) - self.frame(.4)).mean(), .1)
                # H.264 may encode identical source frames with small pixel differences.
                difference = np.abs(self.frame(.56).astype(float) - self.frame(.66))
                self.assertLess(difference.mean(), .1)
                self.assertLessEqual(np.quantile(difference, .999), 4)

    def test_export_presets_and_frame_rates_reach_the_encoder(self):
        self.add_still(motion_style="PAN_RIGHT", pause_after=0.13)
        run = Graph.run
        encodings = []

        def capture(graph, directory, output, maps, encoding, duration):
            if Path(output).name == "output.mp4":
                encodings.append(encoding)
            return run(graph, directory, output, maps, encoding, duration)

        for preset, crf, speed, fps in (("DRAFT", "28", "veryfast", 30), ("HIGH", "18", "slow", 30), ("STANDARD", "23", "fast", 24)):
            with self.subTest(preset=preset):
                self.row.settings.update(export_preset=preset, export_fps=fps)
                self.row.save()
                with patch.object(Graph, "run", capture):
                    make_video(self.row)
                encoding = encodings[-1]
                self.assertEqual(encoding[encoding.index("-crf") + 1], crf)
                self.assertEqual(encoding[encoding.index("-preset") + 1], speed)
                metadata = self.metadata()
                self.assertEqual(metadata["streams"][0]["r_frame_rate"], f"{fps}/1")
                self.assertAlmostEqual(float(metadata["format"]["duration"]), 0.63, delta=0.05)

    def test_frame_rate_changes_rebuild_cached_motion_and_dissolve_clips(self):
        self.add_still(motion_style="PAN_RIGHT", transition_after="DISSOLVE", transition_duration=0.2)
        self.add_still(motion_style="PAN_LEFT")
        self.row.intro = intro.make(file="intro.mp4")
        self.row.outro = outro.make(file="outro.mp4")
        self.row.settings.update(intro_transition="DISSOLVE", intro_transition_duration=0.125)
        make_video(self.row)
        self.row.settings["export_fps"] = 30
        self.row.save()
        with patch("apps.videomanagement.utils.composer.render.render_scene_clip", wraps=render_scene_clip) as build:
            make_video(self.row)
        self.assertEqual(build.call_count, 2)
        self.assertEqual(self.metadata()["streams"][0]["r_frame_rate"], "30/1")
        self.assertAlmostEqual(float(self.metadata()["format"]["duration"]), 1.5, delta=0.05)
        with patch("apps.videomanagement.utils.composer.render.render_scene_clip") as build:
            make_video(self.row)
        build.assert_not_called()

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
                    # The moving intro blends into the scene before it ends;
                    # it must not reappear as a held frame after the boundary.
                    blended = self.frame(0.18).mean(axis=(0, 1))
                    for channel in (0, 2):
                        self.assertGreater(blended[channel], 40)
                        self.assertLess(blended[channel], 220)
                    self.assertGreater(boundary[0], 220)
                    self.assertLess(boundary[2], 20)

    def test_faded_intro_with_audio_tail_does_not_reappear_during_dissolve(self):
        Image.new("RGB", (160, 90), "red").save(self.root / "still.png")
        self.add_still(transition_after="CUT")
        # Smaller source media reproduces the former corner overlay. Its audio
        # also outlasts its video, so seeking near the container end finds no frame.
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i",
                "color=c=blue:s=80x44:r=24:d=0.5,fade=t=out:st=0.125:d=0.125",
                "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=44100:duration=0.75",
                "-t", "0.75", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", str(self.root / "intro-tail.mp4"),
            ],
            check=True, capture_output=True,
        )
        self.row.intro = intro.make(file="intro-tail.mp4")
        self.row.settings.update(intro_transition="DISSOLVE", intro_transition_duration=0.25)
        self.row.save()

        make_video(self.row)

        self.assertGreater(self.frame(0.08)[:, :, 2].mean(), 220)
        self.assertLess(self.frame(0.375).max(), 20)
        blended = self.frame(0.625).mean(axis=(0, 1))
        self.assertGreater(blended[0], 40)
        self.assertLess(blended[0], 220)
        self.assertLess(blended[2], 20)
        after_intro = self.frame(0.75)
        self.assertGreater(after_intro[:, :, 0].min(), 220)
        self.assertLess(after_intro[:, :, 2].max(), 20)
        self.assertAlmostEqual(float(self.metadata()["format"]["duration"]), 1.25, delta=0.05)

    def setUp(self):
        # Rendering fixtures use synthetic tones; speech providers stay mocked.
        self.enterContext(patch("apps.videomanagement.utils.composer.render.align_scene_narration"))
        self.directory = tempfile.TemporaryDirectory(prefix="ffmpeg-tests-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        override = override_settings(
            MEDIA_ROOT=str(self.root), FFMPEG_RENDER_TIMEOUT=60,
            FFMPEG_SCENE_CACHE_ROOT=self.root.parent / (self.root.name + "-cache"),
        )
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, settings.FFMPEG_SCENE_CACHE_ROOT, True)
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

    def decoded_hash(self, stream):
        return subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                self.row.output.path,
                "-map",
                f"0:{stream}",
                "-f",
                "md5",
                "-",
            ]
        )

    def test_direct_export_matches_staged_video_and_audio_with_fractional_timing(self):
        for pause in (0.13, 0.27, 0.09):
            self.add_still(pause_after=pause)
        with override_settings(FFMPEG_DIRECT_RENDER=False, FFMPEG_SCENE_CACHE_BYTES=0):
            make_video(self.row)
        original = (self.decoded_hash("v"), self.decoded_hash("a"))
        with patch(
            "apps.videomanagement.utils.composer.render.render_scene_clip"
        ) as build:
            make_video(self.row)
        build.assert_not_called()
        self.assertEqual((self.decoded_hash("v"), self.decoded_hash("a")), original)

    @override_settings(FFMPEG_DIRECT_RENDER=False)
    def test_repeat_export_reuses_clips_and_still_applies_changed_overlays(self):
        first = self.add_still(motion_style="PAN_RIGHT")
        self.add_still(motion_style="PAN_LEFT")
        with patch(
            "apps.videomanagement.utils.composer.render.render_scene_clip",
            wraps=render_scene_clip,
        ) as build:
            make_video(self.row)
            self.assertEqual(build.call_count, 2)
            original = (self.decoded_hash("v"), self.decoded_hash("a"))
            build.reset_mock()
            make_video(self.row)
            build.assert_not_called()
            self.assertEqual((self.decoded_hash("v"), self.decoded_hash("a")), original)
            overlay = OverlaySerializer(
                data={"kind": "title", "text": "NEW TITLE", "size": 8}
            )
            overlay.is_valid(raise_exception=True)
            first.overlays = [overlay.validated_data]
            first.save(update_fields=["overlays"])
            make_video(self.row)
            build.assert_not_called()
            self.assertNotEqual(self.decoded_hash("v"), original[0])
            self.assertEqual(self.decoded_hash("a"), original[1])

    @override_settings(FFMPEG_DIRECT_RENDER=False)
    def test_source_replacement_invalidates_its_dependent_dissolve_only(self):
        self.add_still(transition_after="DISSOLVE", transition_duration=0.2)
        for color in ("blue", "red"):
            Image.new("RGB", (160, 90), color).save(self.root / f"{color}.png")
            row = self.add_still()
            visual = row.scene_images.get()
            visual.file = f"{color}.png"
            visual.save()
        make_video(self.row)
        Image.new("RGB", (160, 90), "yellow").save(self.root / "still.png")
        with patch(
            "apps.videomanagement.utils.composer.render.render_scene_clip",
            wraps=render_scene_clip,
        ) as build:
            make_video(self.row)
        self.assertEqual(
            [call.args[3].name for call in build.call_args_list],
            ["scene-0.mkv", "scene-1.mkv"],
        )

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
