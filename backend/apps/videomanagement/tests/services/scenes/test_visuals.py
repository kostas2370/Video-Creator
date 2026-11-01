"""Every provider call is stubbed: no image is ever generated or downloaded."""

from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.videomanagement.baker_recipes import narrated_scene, scene, scene_image, video
from apps.videomanagement.integrations.visuals import bing, openai_images
from apps.videomanagement.models import SceneImage
from apps.videomanagement.services.scenes import visuals as scenes_utils
from apps.videomanagement.services.scenes.visuals import (
    create_image_scene,
    create_image_scenes,
    generate_new_image,
    scene_narration_duration,
)
from apps.videomanagement.utils import frames
from apps.videomanagement.utils.frames import still_from_video


class SceneNarrationDurationTests(TestCase):
    def test_reads_the_length_of_the_recorded_line(self):
        row = narrated_scene.make()
        with patch.object(
            scenes_utils, "file_timing", return_value={"audio_duration": 6.5}
        ):
            self.assertEqual(scene_narration_duration(row), 6.5)

    def test_is_zero_when_nothing_was_narrated(self):
        self.assertEqual(scene_narration_duration(scene.make(file=None)), 0)

    def test_is_zero_when_the_recording_cannot_be_read(self):
        with patch.object(scenes_utils, "file_timing", return_value={}):
            self.assertEqual(scene_narration_duration(narrated_scene.make()), 0)


class StillFromVideoTests(SimpleTestCase):
    def test_is_nothing_for_a_still(self):
        self.assertIsNone(still_from_video("a.png", "images/"))

    def test_saves_the_last_visible_frame_including_narration_trimming(self):
        with (
            patch.object(
                frames, "video_metadata", return_value={"duration": 8, "fps": 24}
            ),
            patch.object(frames, "save_video_frame") as save,
        ):
            path = still_from_video("a.mp4", "images/", end_time=5)
        self.assertTrue(path.endswith(".png"))
        self.assertAlmostEqual(save.call_args.args[2], 5 - 1 / 24)

    def test_retries_earlier_frames_when_the_last_frame_will_not_decode(self):
        with (
            patch.object(
                frames,
                "video_metadata",
                return_value={"duration": 0.4, "fps": 24},
            ),
            patch.object(
                frames,
                "save_video_frame",
                side_effect=[OSError("no frame"), None],
            ) as save,
        ):
            self.assertIsNotNone(still_from_video("a.mp4", "images/"))
        self.assertEqual(save.call_count, 2)
        self.assertEqual(save.call_args.args[2], 0.2)

    def test_returns_none_when_no_frame_can_be_read(self):
        with (
            patch.object(
                frames, "video_metadata", return_value={"duration": 8, "fps": 24}
            ),
            patch.object(
                frames, "save_video_frame", side_effect=OSError("no frame")
            ) as save,
        ):
            self.assertIsNone(still_from_video("a.mp4", "images/"))
        self.assertEqual(save.call_count, 3)

    def test_returns_none_when_the_clip_cannot_be_probed(self):
        with patch.object(frames, "video_metadata", side_effect=OSError("bad")):
            self.assertIsNone(still_from_video("a.mp4", "images/"))


class CreateImageSceneTests(TestCase):
    def setUp(self):
        self.video = video.make()
        self.scene = scene.make(video=self.video, text="a sentence")

    def build(self, produced, **kwargs):
        with (
            patch.object(bing.BingImageProvider, "generate", return_value=produced),
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
                bing.BingImageProvider, "generate", side_effect=RuntimeError("no results")
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
            patch.object(bing.BingImageProvider, "generate", return_value="a.png") as download,
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

    def test_series_defaults_to_muted_clip_audio_without_narration(self):
        self.video.settings = dict(narration=False, creation_mode="SERIES")
        create, _ = self.run_with()
        self.assertTrue(create.called)
        self.assertTrue(all(not call.kwargs["with_audio"] for call in create.call_args_list))

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
            create_image_scenes(self.video, mode="AI", provider="OPENAI")
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
            create_image_scenes(self.video, mode="AI", provider="OPENAI")
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
            reference = scenes_utils.scene_reference(appended, self.video, "OPENAI")
        self.assertEqual(reference, self.video.reference_image.path)

    def test_appended_video_scenes_continue_from_the_previous_added_scene(self):
        self.video.gpt_answer = {"scenes": []}
        previous = scene.make(video=self.video, text="An added scene.")
        saved = scene_image.make(scene=previous, file="media/previous.mp4")
        appended = scene.make(video=self.video, text="Another added scene.")
        with (
            patch.object(scenes_utils, "stored_file_exists", return_value=True),
            patch.object(
                scenes_utils, "still_from_video", return_value="images/context.png"
            ) as still,
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
            openai_images.OpenAIImageProvider, "generate", return_value="images/new.png"
        ):
            generate_new_image(self.scene_image, self.video)

        self.scene_image.refresh_from_db()
        self.assertEqual(self.scene_image.file, "images/new.png")

    def test_replacement_preserves_explicit_clip_audio_choices(self):
        self.video.settings = {"creation_mode": "SERIES", "narration": False}
        for keep_audio in (True, False):
            with self.subTest(keep_audio=keep_audio):
                self.scene_image.with_audio = keep_audio
                self.scene_image.save()
                with patch.object(openai_images.OpenAIImageProvider, "generate", return_value="images/new.mp4"):
                    generate_new_image(self.scene_image, self.video)
                self.scene_image.refresh_from_db()
                self.assertEqual(self.scene_image.with_audio, keep_audio)

    def test_keeps_the_old_image_when_generation_fails(self):
        with (
            patch.object(
                openai_images.OpenAIImageProvider,
                "generate",
                side_effect=RuntimeError("rate limit"),
            ),
            self.assertRaisesRegex(RuntimeError, "rate limit"),
        ):
            generate_new_image(self.scene_image, self.video)

        self.scene_image.refresh_from_db()
        self.assertEqual(self.scene_image.file, "media/images/still.png")

    def test_rejects_a_video_whose_mode_has_no_provider(self):
        self.video.mode = "UNKNOWN"

        with (
            patch.object(openai_images.OpenAIImageProvider, "generate") as generate,
            self.assertRaisesRegex(ValueError, "Unsupported visual mode"),
        ):
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
                openai_images.OpenAIImageProvider, "generate", return_value="images/new.png"
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


class ReferenceRoleTests(TestCase):
    def setUp(self):
        self.video = video.make(
            mode="AI", reference_image="media/reference.png",
            settings={"reference_role": "style", "provider": "kling"},
        )

    def test_style_only_video_does_not_use_uploaded_subject_as_first_frame(self):
        with patch.object(scenes_utils, "stored_file_exists", return_value=True):
            self.assertIsNone(scenes_utils.uploaded_reference(self.video, "kling"))
            self.assertEqual(
                scenes_utils.uploaded_reference(self.video, "OPENAI"),
                self.video.reference_image.path,
            )

    def test_style_only_video_keeps_continuity_from_generated_previous_clip(self):
        previous = scene.make(video=self.video, text="First shot")
        scene_image.make(scene=previous, file="media/first.mp4")
        target = scene.make(video=self.video, text="Second shot")
        with patch.object(scenes_utils, "stored_file_exists", return_value=True), patch.object(
            scenes_utils, "continuation_frame", return_value="closing-frame.png",
        ):
            reference = scenes_utils.scene_reference(target, self.video, "kling")
        self.assertEqual(reference, "closing-frame.png")
        self.assertEqual(scenes_utils.reference_role_for(self.video, reference), "both")

    def test_image_regeneration_passes_style_role_for_uploaded_reference(self):
        visual = scene_image.make(scene=scene.make(video=self.video), prompt="A castle")
        self.video.settings["provider"] = "OPENAI"
        with patch.object(scenes_utils, "stored_file_exists", return_value=True), patch.object(
            openai_images.OpenAIImageProvider, "generate", return_value="media/new.png",
        ) as generate:
            generate_new_image(visual, self.video)
        self.assertEqual(generate.call_args.kwargs["reference"], self.video.reference_image.path)
        self.assertEqual(generate.call_args.kwargs["reference_role"], "style")

    def test_character_reference_still_guides_the_first_video_frame(self):
        self.video.settings["reference_role"] = "character"
        first = scene.make(video=self.video)
        with patch.object(scenes_utils, "stored_file_exists", return_value=True):
            reference = scenes_utils.scene_reference(first, self.video, "kling")
        self.assertEqual(reference, self.video.reference_image.path)
        self.assertEqual(scenes_utils.reference_role_for(self.video, reference), "character")

class OpenAIFramePropagationTests(TestCase):
    def test_creation_and_regeneration_forward_each_project_frame(self):
        for frame in ("PORTRAIT", "LANDSCAPE", "SQUARE"):
            with self.subTest(frame=frame):
                project = video.make(
                    mode="AI", settings={"provider": "OPENAI", "video_format": frame}
                )
                row = scene.make(video=project, text="A cat explores")
                with patch.object(
                    scenes_utils.ImageProviderRegistry, "resolve"
                ) as resolve:
                    generate = resolve.return_value
                    generate.return_value = "images/frame-check.png"
                    create_image_scene(
                        project,
                        "A cat",
                        row.text,
                        project.dir_name,
                        mode="AI",
                        provider="OPENAI",
                        scene=row,
                    )
                    self.assertEqual(generate.call_args.kwargs["video_format"], frame)
                    visual = row.scene_images.get()
                    generate_new_image(visual, project)
                    self.assertEqual(generate.call_args.kwargs["video_format"], frame)
