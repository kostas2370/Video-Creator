"""Every provider call is stubbed: no image is ever generated or downloaded."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from ...baker_recipes import narrated_scene, scene, scene_image, user_prompt, video
from ...models import Scene, SceneImage
from ...utils import scenes as scenes_utils
from ...utils.image_providers import bing, openai_images
from ...utils.scenes import (
    create_image_scene,
    create_image_scenes,
    create_twitch_clip_scene,
    generate_new_image,
    scene_narration_duration,
    still_from_video,
)
from ..doubles import FakeAudio


class SceneNarrationDurationTests(TestCase):
    def test_reads_the_length_of_the_recorded_line(self):
        scene = narrated_scene.make()

        with patch.object(
            scenes_utils, "AudioFileClip", return_value=FakeAudio(duration=6.5)
        ):
            self.assertEqual(scene_narration_duration(scene), 6.5)

    def test_is_zero_when_nothing_was_narrated(self):
        silent = scene.make(file=None)

        with patch.object(scenes_utils, "AudioFileClip") as audio:
            self.assertEqual(scene_narration_duration(silent), 0)

        audio.assert_not_called()

    def test_is_zero_when_the_recording_cannot_be_read(self):
        scene = narrated_scene.make()

        with patch.object(scenes_utils, "AudioFileClip", side_effect=OSError("bad")):
            self.assertEqual(scene_narration_duration(scene), 0)


class StillFromVideoTests(SimpleTestCase):
    def test_is_nothing_for_a_still(self):
        self.assertIsNone(still_from_video("a.png", "images/"))

    def test_saves_a_frame_from_near_the_end_of_the_clip(self):
        clip = MagicMock()
        clip.duration = 8.0
        clip.__enter__.return_value = clip

        with patch.object(scenes_utils, "VideoFileClip", return_value=clip):
            path = still_from_video("a.mp4", "images/")

        self.assertTrue(path.endswith(".png"))
        self.assertEqual(clip.save_frame.call_args.kwargs["t"], 7.5)

    def test_tries_earlier_points_when_the_end_of_a_short_clip_will_not_decode(self):
        clip = MagicMock()
        clip.duration = 0.4
        clip.__enter__.return_value = clip
        clip.save_frame.side_effect = [OSError("no frame"), None]

        with patch.object(scenes_utils, "VideoFileClip", return_value=clip):
            self.assertIsNotNone(still_from_video("a.mp4", "images/"))

        self.assertEqual(clip.save_frame.call_count, 2)

    def test_gives_up_quietly_when_no_frame_can_be_read(self):
        clip = MagicMock()
        clip.duration = 8.0
        clip.__enter__.return_value = clip
        clip.save_frame.side_effect = OSError("no frame")

        with patch.object(scenes_utils, "VideoFileClip", return_value=clip):
            self.assertIsNone(still_from_video("a.mp4", "images/"))

    def test_gives_up_quietly_when_the_clip_will_not_open(self):
        with patch.object(scenes_utils, "VideoFileClip", side_effect=OSError("bad")):
            self.assertIsNone(still_from_video("a.mp4", "images/"))


class CreateImageSceneTests(TestCase):
    def setUp(self):
        self.video = video.make()
        self.scene = scene.make(prompt=self.video.prompt, text="a sentence")

    def build(self, produced, **kwargs):
        with (
            patch.object(bing, "download_image", return_value=produced),
            patch.object(scenes_utils, "scene_narration_duration", return_value=4.0),
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
                bing, "download_image", side_effect=RuntimeError("no results")
            ),
            patch.object(scenes_utils, "scene_narration_duration", return_value=0),
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
            patch.object(bing, "download_image", return_value="a.png") as download,
            patch.object(scenes_utils, "scene_narration_duration", return_value=6.5),
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
                scenes_utils,
                "create_image_scene",
                return_value=defaults["create_image_scene"],
            ) as create,
            patch.object(
                scenes_utils,
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
            openai_images, "generate_from_dalle", return_value="images/new.png"
        ):
            generate_new_image(self.scene_image, self.video)

        self.scene_image.refresh_from_db()
        self.assertEqual(self.scene_image.file, "images/new.png")

    def test_keeps_the_old_image_when_generation_fails(self):
        with patch.object(
            openai_images, "generate_from_dalle", side_effect=RuntimeError("rate limit")
        ):
            generate_new_image(self.scene_image, self.video)

        self.scene_image.refresh_from_db()
        self.assertEqual(self.scene_image.file, "media/images/still.png")

    def test_does_nothing_for_a_video_whose_mode_has_no_provider(self):
        self.video.mode = "TWITCH"

        with patch.object(openai_images, "generate_from_dalle") as generate:
            generate_new_image(self.scene_image, self.video)

        generate.assert_not_called()


class CreateTwitchClipSceneTests(TestCase):
    def test_stores_the_clip_as_a_last_scene_that_plays_its_own_sound(self):
        prompt = user_prompt.make()

        with patch.object(
            scenes_utils, "add_text_to_video", return_value="clips/titled.mp4"
        ):
            create_twitch_clip_scene("clips/raw.mp4", "a clip title", prompt)

        scene = Scene.objects.get(prompt=prompt)
        scene_image = SceneImage.objects.get(scene=scene)
        self.assertEqual(scene.text, "a clip title")
        self.assertTrue(scene.is_last)
        self.assertTrue(scene_image.with_audio)
        self.assertEqual(scene_image.file, "clips/titled.mp4")
