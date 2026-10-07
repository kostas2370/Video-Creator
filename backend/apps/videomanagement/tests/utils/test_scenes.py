"""Every provider call is stubbed: no image is ever generated or downloaded."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from ...baker_recipes import narrated_scene, scene, scene_image, video
from ...models import SceneImage
from ...utils import scenes as scenes_utils
from ...utils.image_providers import bing, openai_images
from ...utils.scenes import (
    create_image_scene,
    create_image_scenes,
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
        clip.fps = 24
        clip.__enter__.return_value = clip

        with patch.object(scenes_utils, "VideoFileClip", return_value=clip):
            path = still_from_video("a.mp4", "images/")

        self.assertTrue(path.endswith(".png"))
        self.assertAlmostEqual(clip.save_frame.call_args.kwargs["t"], 8 - 1 / 24)

    def test_tries_earlier_points_when_the_end_of_a_short_clip_will_not_decode(self):
        clip = MagicMock()
        clip.duration = 0.4
        clip.fps = 24
        clip.__enter__.return_value = clip
        clip.save_frame.side_effect = [OSError("no frame"), None]

        with patch.object(scenes_utils, "VideoFileClip", return_value=clip):
            self.assertIsNotNone(still_from_video("a.mp4", "images/"))

        self.assertEqual(clip.save_frame.call_count, 2)

    def test_gives_up_quietly_when_no_frame_can_be_read(self):
        clip = MagicMock()
        clip.duration = 8.0
        clip.fps = 24
        clip.__enter__.return_value = clip
        clip.save_frame.side_effect = OSError("no frame")

        with patch.object(scenes_utils, "VideoFileClip", return_value=clip):
            self.assertIsNone(still_from_video("a.mp4", "images/"))

    def test_gives_up_quietly_when_the_clip_will_not_open(self):
        with patch.object(scenes_utils, "VideoFileClip", side_effect=OSError("bad")):
            self.assertIsNone(still_from_video("a.mp4", "images/"))

    def test_uses_the_last_visible_frame_when_narration_trims_the_clip(self):
        clip = MagicMock(duration=8.0, fps=24)
        clip.__enter__.return_value = clip
        with patch.object(scenes_utils, "VideoFileClip", return_value=clip):
            still_from_video("a.mp4", "images/", end_time=5.0)
        self.assertAlmostEqual(clip.save_frame.call_args.kwargs["t"], 5 - 1 / 24)


class CreateImageSceneTests(TestCase):
    def setUp(self):
        self.video = video.make()
        self.scene = scene.make(video=self.video, text="a sentence")

    def build(self, produced, **kwargs):
        with (
            patch.object(bing, "download_image", return_value=produced),
            patch.object(scenes_utils, "scene_narration_duration", return_value=4.0),
        ):
            create_image_scene(
                video=self.video,
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
                video=self.video,
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
                video=self.video,
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
        mode = patches.pop("mode", "WEB")
        provider = patches.pop("provider", None)
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
            create_image_scenes(self.video, mode=mode, provider=provider)

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
            create_image_scene="images/a.mp4",
            still_from_video="images/anchor.png",
            mode="AI",
            provider="sora",
        )
        self.assertEqual(still.call_count, 2)
        self.assertIsNone(create.call_args_list[0].kwargs["reference"])
        self.assertEqual(
            create.call_args_list[1].kwargs["reference"], "images/anchor.png"
        )

    def test_does_not_anchor_to_a_scene_that_failed_to_generate(self):
        create, still = self.run_with(
            create_image_scene=None, mode="AI", provider="sora"
        )

        still.assert_not_called()

    def add_third_shot(self):
        self.video.gpt_answer["scenes"][0]["sentences"].append(
            {"sentence": "three", "image_description": "cat runs"}
        )

    def test_video_continuation_uses_the_previous_clip_instead_of_the_first(self):
        self.add_third_shot()
        with (
            patch.object(
                scenes_utils,
                "create_image_scene",
                side_effect=["one.mp4", "two.mp4", "three.mp4"],
            ) as create,
            patch.object(
                scenes_utils,
                "still_from_video",
                side_effect=["one.png", "two.png", "three.png"],
            ),
        ):
            create_image_scenes(self.video, mode="AI", provider="sora")
        self.assertEqual(
            [call.kwargs["reference"] for call in create.call_args_list],
            [None, "one.png", "two.png"],
        )

    def test_openai_stills_keep_the_original_identity_reference(self):
        self.add_third_shot()
        with patch.object(
            scenes_utils,
            "create_image_scene",
            side_effect=["one.png", "two.png", "three.png"],
        ) as create:
            create_image_scenes(self.video, mode="AI")
        self.assertEqual(
            [call.kwargs["reference"] for call in create.call_args_list],
            [None, "one.png", "one.png"],
        )

    def test_uploaded_reference_guides_every_openai_image(self):
        self.video.reference_image = "media/reference.png"
        with (
            patch.object(scenes_utils, "stored_file_exists", return_value=True),
            patch.object(
                scenes_utils, "create_image_scene", return_value="shot.png"
            ) as create,
        ):
            create_image_scenes(self.video, mode="AI", provider="DALL-E")
        self.assertEqual(
            [call.kwargs["reference"] for call in create.call_args_list],
            [self.video.reference_image.path] * 2,
        )

    def test_uploaded_reference_starts_sora_then_previous_clip_takes_over(self):
        self.video.reference_image = "media/reference.png"
        with (
            patch.object(scenes_utils, "stored_file_exists", return_value=True),
            patch.object(
                scenes_utils, "create_image_scene", return_value="shot.mp4"
            ) as create,
            patch.object(scenes_utils, "still_from_video", return_value="end.png"),
        ):
            create_image_scenes(self.video, mode="AI", provider="sora")
        self.assertEqual(
            [call.kwargs["reference"] for call in create.call_args_list],
            [self.video.reference_image.path, "end.png"],
        )

    def test_resume_restores_the_preceding_completed_clip(self):
        self.add_third_shot()
        first = scene.make(video=self.video, text="one")
        second = scene.make(video=self.video, text="two")
        scene_image.make(scene=first, file="media/one.mp4")
        saved = scene_image.make(scene=second, file="media/two.mp4")
        with (
            patch.object(scenes_utils, "stored_file_exists", return_value=True),
            patch.object(
                scenes_utils, "create_image_scene", return_value="three.mp4"
            ) as create,
            patch.object(
                scenes_utils,
                "still_from_video",
                side_effect=lambda path, folder: path + ".png",
            ),
        ):
            create_image_scenes(self.video, mode="AI", provider="sora")
        create.assert_called_once()
        self.assertEqual(create.call_args.kwargs["reference"], saved.file.path + ".png")

    def test_resume_restores_the_original_image_anchor(self):
        first = scene.make(video=self.video, text="one")
        # Failed attempts must not hide a later successful visual.
        scene_image.make(scene=first, file=None)
        saved = scene_image.make(scene=first, file="media/one.png")
        with (
            patch.object(
                scenes_utils,
                "stored_file_exists",
                side_effect=lambda field: bool(field),
            ),
            patch.object(
                scenes_utils, "create_image_scene", return_value="two.png"
            ) as create,
        ):
            create_image_scenes(self.video, mode="AI", provider="DALL-E")
        create.assert_called_once()
        self.assertEqual(create.call_args.kwargs["reference"], saved.file.path)

    def test_failed_clip_breaks_the_continuation_chain(self):
        self.add_third_shot()
        with (
            patch.object(
                scenes_utils,
                "create_image_scene",
                side_effect=["one.mp4", None, "three.mp4"],
            ) as create,
            patch.object(scenes_utils, "still_from_video", return_value="one.png"),
        ):
            create_image_scenes(self.video, mode="AI", provider="sora")
        self.assertIsNone(create.call_args_list[2].kwargs["reference"])

    def test_continuation_accounts_for_narration_trimming(self):
        narrated_scene.make(video=self.video, text="one")
        with (
            patch.object(scenes_utils, "scene_narration_duration", return_value=5),
            patch.object(scenes_utils, "still_from_video") as still,
        ):
            scenes_utils.continuation_frame(self.video, "one", "one.mp4")
        self.assertEqual(still.call_args.kwargs["end_time"], 5)


class GenerateNewImageTests(TestCase):
    def test_appended_scenes_reuse_the_uploaded_identity_image(self):
        self.video.reference_image = "media/context.png"
        appended = scene.make(video=self.video, text="Added after generation.")
        with patch.object(scenes_utils, "stored_file_exists", return_value=True):
            reference = scenes_utils.scene_reference(appended, self.video, "DALL-E")
        self.assertEqual(reference, self.video.reference_image.path)

    def test_appended_video_scenes_continue_from_the_previous_added_scene(self):
        self.video.gpt_answer = {"scenes": []}
        previous = scene.make(video=self.video, text="An added scene.")
        saved = scene_image.make(scene=previous, file="media/previous.mp4")
        appended = scene.make(video=self.video, text="Another added scene.")
        with (
            patch.object(scenes_utils, "stored_file_exists", return_value=True),
            patch.object(scenes_utils, "still_from_video", return_value="images/context.png") as still,
        ):
            reference = scenes_utils.scene_reference(appended, self.video, "sora")
        self.assertEqual(reference, "images/context.png")
        self.assertEqual(still.call_args.args[0], saved.file.path)

    def test_a_missing_previous_clip_does_not_reuse_an_older_frame(self):
        scene.make(video=self.video, text="Missing previous clip.")
        appended = scene.make(video=self.video, text="Next scene.")
        with patch.object(scenes_utils, "still_from_video") as still:
            reference = scenes_utils.scene_reference(appended, self.video, "sora")
        self.assertIsNone(reference)
        still.assert_not_called()

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
        self.video.mode = "UNKNOWN"

        with patch.object(openai_images, "generate_from_dalle") as generate:
            generate_new_image(self.scene_image, self.video)

        generate.assert_not_called()

    def test_regeneration_reuses_the_first_image_reference(self):
        self.video.gpt_answer = {
            "scenes": [
                {
                    "sentences": [
                        {"sentence": "one", "image_description": "cat"},
                        {"sentence": "two", "image_description": "cat running"},
                    ]
                }
            ]
        }
        first = scene.make(video=self.video, text="one")
        saved = scene_image.make(scene=first, file="media/anchor.png")
        with (
            patch.object(scenes_utils, "stored_file_exists", return_value=True),
            patch.object(
                openai_images, "generate_from_dalle", return_value="images/new.png"
            ) as generate,
        ):
            generate_new_image(self.scene_image, self.video)
        self.assertEqual(generate.call_args.kwargs["reference"], saved.file.path)

    def test_video_regeneration_uses_its_predecessor_not_a_later_clip(self):
        self.video.gpt_answer = {
            "scenes": [
                {
                    "sentences": [
                        {"sentence": "one", "image_description": "cat"},
                        {"sentence": "two", "image_description": "cat running"},
                        {"sentence": "three", "image_description": "cat sleeps"},
                    ]
                }
            ]
        }
        first = scene.make(video=self.video, text="one")
        second = scene.make(video=self.video, text="two")
        saved = scene_image.make(scene=first, file="media/one.mp4")
        target = scene_image.make(scene=second, file="media/two.mp4")
        with (
            patch.object(scenes_utils, "stored_file_exists", return_value=True),
            patch.object(
                scenes_utils, "still_from_video", return_value="anchor.png"
            ) as still,
        ):
            reference = scenes_utils.scene_reference(target.scene, self.video, "sora")
        self.assertEqual(reference, "anchor.png")
        self.assertEqual(still.call_args.args[0], saved.file.path)
