"""Every provider call is stubbed: no OpenAI, Bing, Google or YouTube request is made."""

import base64
import tempfile
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import APIException

from ..baker_recipes import (
    music,
    narrated_scene,
    scene,
    scene_image,
    user_prompt,
    video,
)
from ..models import Music, Scene, SceneImage
from ..utils import visual_utils
from ..utils.visual_utils import (
    create_image_scene,
    create_image_scenes,
    create_twitch_clip_scene,
    download_image,
    download_image_from_google,
    download_music,
    generate_from_dalle,
    generate_from_sora,
    generate_new_image,
    scene_narration_duration,
    still_from_video,
)
from .doubles import FakeAudio


class SceneNarrationDurationTests(TestCase):
    def test_reads_the_length_of_the_recorded_line(self):
        scene = narrated_scene.make()

        with patch.object(
            visual_utils, "AudioFileClip", return_value=FakeAudio(duration=6.5)
        ):
            self.assertEqual(scene_narration_duration(scene), 6.5)

    def test_is_zero_when_nothing_was_narrated(self):
        silent = scene.make(file=None)

        with patch.object(visual_utils, "AudioFileClip") as audio:
            self.assertEqual(scene_narration_duration(silent), 0)

        audio.assert_not_called()

    def test_is_zero_when_the_recording_cannot_be_read(self):
        scene = narrated_scene.make()

        with patch.object(visual_utils, "AudioFileClip", side_effect=OSError("bad")):
            self.assertEqual(scene_narration_duration(scene), 0)


class GenerateFromSoraTests(SimpleTestCase):
    def setUp(self):
        self.video = MagicMock(status="completed", id="vid_1")
        self.client = MagicMock()
        self.client.videos.create_and_poll.return_value = self.video
        patcher = patch.object(visual_utils, "OpenAI", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def generate(self, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            kwargs.setdefault("prompt", "a cat naps")
            kwargs.setdefault("dir_name", f"{tmp}/")
            return generate_from_sora(**kwargs)

    def requested_seconds(self, duration):
        self.generate(duration=duration)
        return self.client.videos.create_and_poll.call_args.kwargs["seconds"]

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_asks_for_the_shortest_clip_that_covers_the_narration(self):
        self.assertEqual(self.requested_seconds(3.0), "4")
        self.assertEqual(self.requested_seconds(5.0), "8")
        self.assertEqual(self.requested_seconds(9.0), "12")

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_caps_a_long_sentence_at_the_longest_clip_sora_renders(self):
        # handle_video covers the rest by holding the final frame.
        self.assertEqual(self.requested_seconds(30.0), "12")

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_falls_back_to_the_silent_scene_length_with_no_narration_to_fit(self):
        # Not the 4s minimum: a silent scene would otherwise collapse by accident.
        self.assertEqual(self.requested_seconds(0), "8")

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7, SORA_STYLE="noir")
    def test_carries_the_shared_style_into_every_shot(self):
        self.generate(duration=4.0, title="Cats")

        prompt = self.client.videos.create_and_poll.call_args.kwargs["prompt"]
        self.assertIn("noir", prompt)
        self.assertIn("a cat naps", prompt)

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_anchors_the_shot_to_a_reference_frame_when_one_exists(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as anchor:
            self.generate(duration=4.0, reference=anchor.name)

        self.assertIn(
            "input_reference", self.client.videos.create_and_poll.call_args.kwargs
        )

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_ignores_a_reference_frame_that_is_not_on_disk(self):
        self.generate(duration=4.0, reference="/nowhere/anchor.png")

        self.assertNotIn(
            "input_reference", self.client.videos.create_and_poll.call_args.kwargs
        )

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_raises_with_the_providers_reason_when_the_job_does_not_complete(self):
        self.video.status = "failed"
        self.video.error = MagicMock(code="moderation", message="blocked")

        with self.assertRaises(APIException) as caught:
            self.generate(duration=4.0)

        self.assertIn("moderation", str(caught.exception))

    @override_settings(OPEN_API_KEY="key", SILENT_SCENE_SECONDS=7)
    def test_writes_the_finished_clip_as_an_mp4(self):
        path = self.generate(duration=4.0)

        self.assertTrue(path.endswith(".mp4"))
        self.client.videos.download_content.assert_called_once()


class GenerateFromDalleTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.client = MagicMock()
        self.client.images.generate.return_value.data = [
            MagicMock(b64_json=base64.b64encode(b"a png").decode())
        ]
        patcher = patch.object(visual_utils, "OpenAI", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    @override_settings(
        OPEN_API_KEY="key",
        IMAGE_MODEL="gpt-image-1",
        IMAGE_SIZE="1024x1024",
        IMAGE_QUALITY="high",
    )
    def test_decodes_the_image_to_a_png(self):
        path = generate_from_dalle("a cat", f"{self.tmp.name}/", style="vivid")

        self.assertTrue(path.endswith(".png"))
        self.assertEqual(open(path, "rb").read(), b"a png")

    @override_settings(
        OPEN_API_KEY="key",
        IMAGE_MODEL="gpt-image-1",
        IMAGE_SIZE="1024x1024",
        IMAGE_QUALITY="high",
    )
    def test_folds_the_style_into_the_prompt(self):
        # gpt-image has no `style` argument — that was DALL-E 3 only.
        generate_from_dalle("a cat", f"{self.tmp.name}/", style="vivid", title="Cats")

        kwargs = self.client.images.generate.call_args.kwargs
        self.assertIn("Style: vivid", kwargs["prompt"])
        self.assertNotIn("style", kwargs)

    @override_settings(
        OPEN_API_KEY="key",
        IMAGE_MODEL="gpt-image-1",
        IMAGE_SIZE="1024x1024",
        IMAGE_QUALITY="high",
    )
    def test_raises_when_the_model_returns_no_image(self):
        self.client.images.generate.return_value.data = []

        with self.assertRaises(APIException):
            generate_from_dalle("a cat", f"{self.tmp.name}/", style="vivid")


class DownloadImageTests(SimpleTestCase):
    def test_returns_the_first_result_from_bing(self):
        with patch.object(
            visual_utils.downloader, "download", return_value=(["a.png"], 1)
        ):
            self.assertEqual(download_image("a cat", "images/"), ["a.png"])

    def test_returns_nothing_when_bing_fails_rather_than_breaking_the_scene(self):
        with patch.object(
            visual_utils.downloader, "download", side_effect=RuntimeError("no results")
        ):
            self.assertIsNone(download_image("a cat", "images/"))

    def test_returns_the_google_result(self):
        with patch.object(
            visual_utils.google_downloader, "download", return_value="a.png"
        ):
            self.assertEqual(download_image_from_google("a cat", "images/"), "a.png")

    def test_returns_nothing_when_google_fails(self):
        with patch.object(
            visual_utils.google_downloader, "download", side_effect=RuntimeError("429")
        ):
            self.assertIsNone(download_image_from_google("a cat", "images/"))


class StillFromVideoTests(SimpleTestCase):
    def test_is_nothing_for_a_still(self):
        self.assertIsNone(still_from_video("a.png", "images/"))

    def test_saves_a_frame_from_near_the_end_of_the_clip(self):
        clip = MagicMock()
        clip.duration = 8.0
        clip.__enter__.return_value = clip

        with patch.object(visual_utils, "VideoFileClip", return_value=clip):
            path = still_from_video("a.mp4", "images/")

        self.assertTrue(path.endswith(".png"))
        self.assertEqual(clip.save_frame.call_args.kwargs["t"], 7.5)

    def test_tries_earlier_points_when_the_end_of_a_short_clip_will_not_decode(self):
        clip = MagicMock()
        clip.duration = 0.4
        clip.__enter__.return_value = clip
        clip.save_frame.side_effect = [OSError("no frame"), None]

        with patch.object(visual_utils, "VideoFileClip", return_value=clip):
            self.assertIsNotNone(still_from_video("a.mp4", "images/"))

        self.assertEqual(clip.save_frame.call_count, 2)

    def test_gives_up_quietly_when_no_frame_can_be_read(self):
        clip = MagicMock()
        clip.duration = 8.0
        clip.__enter__.return_value = clip
        clip.save_frame.side_effect = OSError("no frame")

        with patch.object(visual_utils, "VideoFileClip", return_value=clip):
            self.assertIsNone(still_from_video("a.mp4", "images/"))

    def test_gives_up_quietly_when_the_clip_will_not_open(self):
        with patch.object(visual_utils, "VideoFileClip", side_effect=OSError("bad")):
            self.assertIsNone(still_from_video("a.mp4", "images/"))


class CreateImageSceneTests(TestCase):
    def setUp(self):
        self.video = video.make()
        self.scene = scene.make(prompt=self.video.prompt, text="a sentence")

    def build(self, produced, **kwargs):
        with (
            patch.object(visual_utils, "download_image", return_value=produced),
            patch.object(visual_utils, "scene_narration_duration", return_value=4.0),
        ):
            create_image_scene(
                prompt=self.video.prompt,
                image="a cat",
                text="a sentence",
                dir_name=self.video.dir_name,
                mode="WEB",
                provider="bing",
                **kwargs,
            )

        return SceneImage.objects.get(scene=self.scene)

    def test_records_the_generated_visual_against_the_scene(self):
        scene_image = self.build("images/a.png")

        self.assertEqual(scene_image.file, "images/a.png")
        self.assertEqual(scene_image.prompt, "a cat")

    def test_leaves_the_scene_image_empty_when_generation_failed(self):
        with (
            patch.object(
                visual_utils, "download_image", side_effect=RuntimeError("no results")
            ),
            patch.object(visual_utils, "scene_narration_duration", return_value=0),
        ):
            create_image_scene(
                prompt=self.video.prompt,
                image="a cat",
                text="a sentence",
                dir_name=self.video.dir_name,
                mode="WEB",
                provider="bing",
            )

        self.assertFalse(SceneImage.objects.get(scene=self.scene).file)

    def test_tells_the_provider_how_long_the_sentence_is_spoken_for(self):
        with (
            patch.object(
                visual_utils, "download_image", return_value="a.png"
            ) as download,
            patch.object(visual_utils, "scene_narration_duration", return_value=6.5),
        ):
            create_image_scene(
                prompt=self.video.prompt,
                image="a cat",
                text="a sentence",
                dir_name=self.video.dir_name,
                mode="WEB",
                provider="bing",
            )

        self.assertEqual(download.call_args.kwargs["duration"], 6.5)

    def test_plays_a_generated_clips_own_sound_when_asked_to(self):
        self.assertTrue(self.build("images/a.mp4", with_audio=True).with_audio)

    def test_never_flags_a_still_to_play_sound(self):
        # A png has nothing to play, whatever the video's narration setting.
        self.assertFalse(self.build("images/a.png", with_audio=True).with_audio)

    def test_never_flags_a_visual_that_was_never_produced(self):
        self.assertFalse(self.build(None, with_audio=True).with_audio)

    def test_leaves_a_clip_silent_by_default(self):
        self.assertFalse(self.build("images/a.mp4").with_audio)


class CreateImageScenesTests(TestCase):
    def setUp(self):
        self.video = video.make()
        self.video.gpt_answer = {
            "scenes": [
                {
                    "sentences": [
                        {"sentence": "one", "image_description": "a cat"},
                        {"sentence": "two", "image_description": "a dog"},
                    ]
                }
            ]
        }

    def run_with(self, **patches):
        defaults = dict(create_image_scene="images/a.png", still_from_video=None)
        defaults.update(patches)
        with (
            patch.object(
                visual_utils,
                "create_image_scene",
                return_value=defaults["create_image_scene"],
            ) as create,
            patch.object(
                visual_utils,
                "still_from_video",
                return_value=defaults["still_from_video"],
            ) as still,
        ):
            create_image_scenes(self.video, mode="WEB")

        return create, still

    def test_generates_a_visual_for_every_sentence(self):
        create, _ = self.run_with()

        self.assertEqual(create.call_count, 2)

    def test_keeps_a_narrated_videos_clips_silent(self):
        create, _ = self.run_with()

        self.assertFalse(create.call_args.kwargs["with_audio"])

    def test_lets_the_clips_play_their_own_sound_when_there_is_no_narration(self):
        self.video.settings = dict(narration=False)

        create, _ = self.run_with()

        self.assertTrue(create.call_args.kwargs["with_audio"])

    def test_narrates_by_default_when_the_video_has_no_settings(self):
        self.video.settings = None

        create, _ = self.run_with()

        self.assertFalse(create.call_args.kwargs["with_audio"])

    def test_anchors_later_shots_to_the_look_of_the_first(self):
        create, still = self.run_with(
            create_image_scene="images/a.mp4", still_from_video="images/anchor.png"
        )
        self.assertEqual(still.call_count, 1)
        self.assertIsNone(create.call_args_list[0].kwargs["reference"])
        self.assertEqual(
            create.call_args_list[1].kwargs["reference"], "images/anchor.png"
        )

    def test_does_not_anchor_to_a_scene_that_failed_to_generate(self):
        create, still = self.run_with(create_image_scene=None)

        still.assert_not_called()


class GenerateNewImageTests(TestCase):
    def setUp(self):
        self.video = video.make(mode="AI")
        self.scene_image = scene_image.make()

    def test_replaces_the_file_with_the_newly_generated_one(self):
        with patch.object(
            visual_utils, "generate_from_dalle", return_value="images/new.png"
        ):
            generate_new_image(self.scene_image, self.video)

        self.scene_image.refresh_from_db()
        self.assertEqual(self.scene_image.file, "images/new.png")

    def test_keeps_the_old_image_when_generation_fails(self):
        with patch.object(
            visual_utils, "generate_from_dalle", side_effect=RuntimeError("rate limit")
        ):
            generate_new_image(self.scene_image, self.video)

        self.scene_image.refresh_from_db()
        self.assertEqual(self.scene_image.file, "media/images/still.png")

    def test_does_nothing_for_a_video_whose_mode_has_no_provider(self):
        self.video.mode = "TWITCH"

        with patch.object(visual_utils, "generate_from_dalle") as generate:
            generate_new_image(self.scene_image, self.video)

        generate.assert_not_called()


class DownloadMusicTests(TestCase):
    def test_downloads_nothing_for_a_blank_url(self):
        for url in (None, "", "None"):
            with self.subTest(url=url):
                self.assertIsNone(download_music(url))

    def test_reuses_music_that_was_already_downloaded(self):
        existing = music.make(name="a song")
        youtube = MagicMock()
        youtube.streams.filter.return_value.first.return_value.title = "a song"

        with patch.object(visual_utils, "YouTube", return_value=youtube):
            self.assertEqual(download_music("https://youtu.be/x"), existing)

        self.assertEqual(Music.objects.count(), 1)

    def test_stores_a_newly_downloaded_track(self):
        youtube = MagicMock()
        youtube.title = "a new song"
        stream = youtube.streams.filter.return_value.first.return_value
        stream.title = "a new song"
        stream.download.return_value = "media/music/raw.webm"

        with (
            patch.object(visual_utils, "YouTube", return_value=youtube),
            patch.object(visual_utils.os, "rename"),
        ):
            music = download_music("https://youtu.be/x")

        self.assertEqual(music.name, "a new song")
        self.assertTrue(music.file.name.endswith(".mp3"))


class CreateTwitchClipSceneTests(TestCase):
    def test_stores_the_clip_as_a_last_scene_that_plays_its_own_sound(self):
        prompt = user_prompt.make()

        with patch.object(
            visual_utils, "add_text_to_video", return_value="clips/titled.mp4"
        ):
            create_twitch_clip_scene("clips/raw.mp4", "a clip title", prompt)

        scene = Scene.objects.get(prompt=prompt)
        scene_image = SceneImage.objects.get(scene=scene)
        self.assertEqual(scene.text, "a clip title")
        self.assertTrue(scene.is_last)
        self.assertTrue(scene_image.with_audio)
        self.assertEqual(scene_image.file, "clips/titled.mp4")
