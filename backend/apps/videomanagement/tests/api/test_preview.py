
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import intro, outro, scene, scene_image
from ...models import Video
from ...serializers.preview import PreviewTimelineSerializer
from ...utils.motion import resolved_motion
from ...utils.timing import media_timing
from .base import ApiTestCase


class PreviewTests(ApiTestCase):
    def test_photo_animation_plan_and_fps_are_in_preview_but_not_for_clips(self):
        self.first.animation_preset = "PLAYFUL"
        self.first.save()
        self.video.settings["export_fps"] = 30
        self.video.save()
        data = self.client.get(self.url).data
        first = next(segment for segment in data["segments"] if segment["id"] == str(self.first.pk))
        self.assertEqual(first["photo_animation"]["preset"], "PLAYFUL")
        self.assertEqual(first["fps"], 30)
        image = self.first.scene_images.first()
        image.file = "clip.mp4"
        image.save()
        first = next(segment for segment in self.client.get(self.url).data["segments"] if segment["id"] == str(self.first.pk))
        self.assertIsNone(first["photo_animation"])

    def test_tiktok_style_is_saved_and_preview_exposes_word_highlights(self):
        response = self.client.patch(reverse("video-detail", args=[self.video.pk]), {"caption_style": "TIKTOK"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        data = self.client.get(self.url).data
        self.assertEqual(data["caption_style"], "TIKTOK")
        self.assertTrue(data["captions"])
        self.assertTrue(all(cue["active_word"] is not None for cue in data["captions"]))
        self.assertTrue(all(len(cue["text"].split()) <= 4 for cue in data["captions"]))
        response = self.client.patch(reverse("video-detail", args=[self.video.pk]), {"caption_style": "UNKNOWN"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_intro_effects_are_independent_of_scene_defaults_and_keep_caption_offsets(self):
        self.video.intro = intro.make(file="speech.wav", created_by=self.user)
        for style, expected in (("CUT", (0, 0, 0)), ("FADE", (0.25, 0.25, 0)), ("DISSOLVE", (0, 0, 0.25))):
            with self.subTest(style=style):
                self.video.settings.update(intro_transition=style, intro_transition_duration=0.25)
                self.video.save()
                data = self.client.get(self.url).data
                opening, first, second = data["segments"]
                self.assertEqual((opening["fade_out"], first["fade_in"], first["dissolve_in"]), expected)
                self.assertEqual(second["dissolve_in"], 0.5)
                self.assertEqual(first["start"], 2)
                self.assertEqual(data["captions"][0]["start"], 2)
                self.assertEqual(data["duration"], 6.75)

    def test_intro_inherits_defaults_clamps_short_clips_and_is_ignored_without_intro(self):
        self.video.intro = intro.make(file="speech.wav", created_by=self.user)
        self.video.settings.update(intro_transition="DEFAULT", intro_transition_duration=3)
        self.video.save()
        segments = self.client.get(self.url).data["segments"]
        self.assertEqual(segments[0]["transition"], "DISSOLVE")
        self.assertEqual(segments[1]["dissolve_in"], 1)
        self.video.intro = None
        self.video.settings.update(transition_default="CUT", intro_transition="FADE")
        self.video.save()
        first = self.client.get(self.url).data["segments"][0]
        self.assertEqual((first["fade_in"], first["dissolve_in"]), (0, 0))

    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        override = override_settings(MEDIA_ROOT=self.directory.name)
        override.enable()
        self.addCleanup(override.disable)
        with wave.open(str(Path(self.directory.name, "speech.wav")), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * 16000)
        Path(self.directory.name, "picture.png").write_bytes(b"demo image")
        self.video = self.video_for(status="READY", settings={"narration": True, "subtitles": True,
                                                             "transition_default": "DISSOLVE", "transition_duration": 0.5})
        self.first = scene.make(video=self.video, file="speech.wav", text="First sentence.", pause_after=0.75)
        self.second = scene.make(video=self.video, file="speech.wav", text="Second sentence.")
        scene_image.make(scene=self.first, file="picture.png", with_audio=False)
        self.url = reverse("video-preview", args=[self.video.pk])

    def test_series_preview_defaults_to_cuts_including_the_first_frame(self):
        self.video.settings = {"narration": False, "creation_mode": "SERIES"}
        self.video.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for segment in response.data["segments"]:
            self.assertEqual(segment["transition"], "CUT")
            self.assertEqual((segment["fade_in"], segment["fade_out"], segment["dissolve_in"]), (0, 0, 0))
        self.first.transition_after = "DISSOLVE"
        self.first.transition_duration = 0.25
        self.first.save()
        segments = self.client.get(self.url).data["segments"]
        self.assertEqual(segments[1]["dissolve_in"], 0.25)

    def test_preview_resolves_auto_motion_for_images_only(self):

        self.first.motion_style = "AUTO"
        self.first.motion_intensity = "STRONG"
        self.first.save()
        segments = self.client.get(self.url).data["segments"]
        self.assertEqual(segments[0]["motion_style"], resolved_motion(self.first))
        self.assertEqual(segments[0]["motion_intensity"], "STRONG")
        visual = self.first.scene_images.get()
        visual.file = "clip.mp4"
        visual.save()
        self.assertEqual(self.client.get(self.url).data["segments"][0]["motion_style"], "NONE")

    def test_timeline_and_captions_share_pauses_and_intro_offsets_without_charging(self):
        self.video.intro = intro.make(file="speech.wav", created_by=self.user)
        self.video.outro = outro.make(file="speech.wav", created_by=self.user)
        self.video.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        data = response.data
        self.assertEqual(data["duration"], 8.75)
        self.assertEqual([s["start"] for s in data["segments"]], [0, 2, 4.75, 6.75])
        self.assertEqual([c["start"] for c in data["captions"]], [2, 4.75])
        self.assertEqual(data["segments"][1]["pause"], 0.75)
        self.assertEqual(data["segments"][1]["fade_in"], 0)
        self.assertEqual(data["segments"][2]["dissolve_in"], 0.5)
        self.assertEqual(data["segments"][2]["visual"], None)

    def test_reorder_overrides_and_missing_audio(self):
        self.first.transition_after = "CUT"
        self.first.file = None
        self.first.save()
        data = self.client.get(self.url).data
        self.assertEqual(data["segments"][0]["duration"], 1.75)
        self.assertIsNone(data["segments"][0]["narration"])
        self.assertEqual(data["segments"][1]["dissolve_in"], 0)
        self.assertEqual(data["captions"][0]["start"], 1.75)
        self.first.position = 3
        self.first.save()
        self.second.position = 1
        self.second.save()
        self.assertEqual(self.client.get(self.url).data["segments"][0]["id"], str(self.second.pk))

    def test_silent_clip_sound_and_ending_holds(self):
        self.first.is_last = True
        self.first.save()
        self.assertEqual(self.client.get(self.url).data["segments"][0]["duration"], 4.75)
        self.video.settings = {"narration": False, "subtitles": True, "video_format": "PORTRAIT"}
        self.video.save()
        visual = self.first.scene_images.get()
        visual.file = "clip.mp4"
        visual.with_audio = True
        visual.save()
        Path(self.directory.name, "clip.mp4").write_bytes(b"demo video")
        original = media_timing
        def timing(path):
            if str(path).endswith("clip.mp4"):
                return {"duration": 5, "audio_duration": 5}
            return original(path)
        with patch("apps.videomanagement.utils.timing.media_timing", side_effect=timing):
            data = self.client.get(self.url).data
        self.assertEqual(data["size"], [1080, 1920])
        self.assertEqual(data["captions"], [])
        self.assertTrue(data["segments"][0]["clip_audio"])
        self.assertIsNone(data["segments"][0]["narration"])
        self.assertEqual(data["segments"][0]["duration"], 5.75)

    def test_fade_duration_is_clipped_and_no_captions_when_disabled(self):
        self.first.transition_after = "FADE"
        self.first.transition_duration = 3
        self.first.save()
        self.video.settings = {"subtitles": False}
        self.video.save()
        data = self.client.get(self.url).data
        self.assertEqual(data["segments"][0]["fade_out"], 1.375)
        self.assertEqual(data["segments"][1]["fade_in"], 1)
        self.assertEqual(data["captions"], [])

    def test_private_processing_and_invalid_assets(self):
        for status in ("GENERATION", "RENDERING", "REVIEW"):
            self.video.status = status
            self.video.save()
            self.assertEqual(self.client.get(self.url).status_code, 409)
        self.video.status = "FAILED"
        self.video.intro = intro.make(file="missing.mp4", created_by=self.user)
        self.video.save()
        self.assertEqual(self.client.get(self.url).status_code, 400)
        foreign = self.video_for(owner=user.make())
        self.assertEqual(self.client.get(reverse("video-preview", args=[foreign.pk])).status_code, 404)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_no_scenes_is_actionable(self):
        self.video.scenes.all().delete()
        self.assertEqual(self.client.get(self.url).status_code, 400)
        self.assertIn("Add a scene", self.client.get(self.url).data["detail"])

    def test_serializer_reads_prefetched_video_models_without_extra_queries(self):
        self.video.intro = intro.make(file="speech.wav", created_by=self.user)
        self.video.outro = outro.make(file="speech.wav", created_by=self.user)
        self.video.save()
        video = Video.objects.select_related("intro", "outro").prefetch_related(
            "scenes__scene_images__asset",
        ).get(pk=self.video.pk)
        with self.assertNumQueries(0):
            data = PreviewTimelineSerializer(video).data
        intro_data, first, second, outro_data = data["segments"]
        self.assertEqual(first["id"], str(self.first.pk))
        self.assertEqual(first["text"], self.first.text)
        self.assertEqual(first["pause"], self.first.pause_after)
        self.assertEqual(first["label"], "Scene 1")
        self.assertEqual(first["visual"], self.first.scene_images.get().file.url)
        self.assertEqual(first["narration"], self.first.file.url)
        self.assertEqual(second["text"], self.second.text)
        self.assertIsNone(second["visual"])
        for segment, asset, kind in ((intro_data, video.intro, "intro"), (outro_data, video.outro, "outro")):
            self.assertEqual(segment["id"], f"{kind}-{asset.pk}")
            self.assertEqual(segment["visual"], asset.file.url)
            self.assertIsNone(segment["text"])
            self.assertIsNone(segment["narration"])
            self.assertEqual(segment["pause"], 0)

    def test_unusable_scene_visual_is_not_exposed(self):
        visual = self.first.scene_images.get()
        visual.file = "speech.wav"
        visual.save()
        self.assertIsNone(self.client.get(self.url).data["segments"][0]["visual"])
        visual = self.first.scene_images.get()
        visual.file = "missing.png"
        visual.save()
        self.assertIsNone(self.client.get(self.url).data["segments"][0]["visual"])

    def test_opening_uses_video_default_instead_of_scene_outgoing_override(self):
        self.first.transition_after = "FADE"
        self.first.save()
        for style, expected in (("CUT", 0), ("DISSOLVE", 0), ("FADE", 0.5)):
            with self.subTest(style=style):
                self.video.settings = {"transition_default": style, "transition_duration": 0.5}
                self.video.save()
                first = self.client.get(self.url).data["segments"][0]
                self.assertEqual(first["fade_in"], expected)
                self.assertEqual(first["fade_out"], 0.5)
