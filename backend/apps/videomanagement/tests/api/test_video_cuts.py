from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.videomanagement.baker_recipes import scene
from .base import ApiTestCase


class VideoCutsTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.video = self.video_for(settings={"narration": False, "subtitles": False})
        self.first = scene.make(video=self.video, audio_settings={"duration": 5})
        self.second = scene.make(video=self.video, audio_settings={"duration": 5})
        self.url = reverse("video-cuts", args=[self.video.pk])
        self.preview_url = reverse("video-preview", args=[self.video.pk])

    def payload(self, sections=None):
        manifest = self.client.get(self.preview_url).data
        return {
            "source_duration": manifest["cut_source"]["duration"],
            "source_key": manifest["cut_source"]["key"],
            "previous": manifest.get("cuts", self.video.cuts),
            "sections": sections or [{"start": 2, "end": 8}],
        }

    def test_cuts_across_scenes_and_preserves_scene_data(self):
        payload = self.payload()
        response = self.client.patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["cuts"]["sections"], payload["sections"])
        preview = self.client.get(self.preview_url).data
        self.assertEqual(
            preview["playback_sections"],
            [{"start": 2, "end": 5}, {"start": 5, "end": 8}],
        )
        self.assertEqual(preview["cut_source"]["duration"], 10)
        self.assertFalse(preview["cuts_stale"])
        self.assertEqual(response.data["cut_summary"], {"duration": 6, "stale": False})
        self.first.refresh_from_db()
        self.assertEqual(self.first.cuts, {})
        self.assertEqual(self.video.scenes.count(), 2)
        self.assertEqual(
            self.client.patch(self.url, payload, format="json").status_code, 409
        )

    def test_composes_with_existing_scene_cuts_and_can_restore_full_video(self):
        self.first.cuts = {"source_duration": 5, "sections": [{"start": 1, "end": 3}]}
        self.first.save()
        payload = self.payload([{"start": 1, "end": 4}])
        self.assertEqual(payload["source_duration"], 7)
        response = self.client.patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            self.client.get(self.preview_url).data["playback_sections"],
            [{"start": 2, "end": 3}, {"start": 5, "end": 7}],
        )
        self.video.refresh_from_db()
        payload = self.payload([{"start": 0, "end": 7}])
        response = self.client.patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            self.client.get(self.preview_url).data["playback_sections"],
            [{"start": 1, "end": 3}, {"start": 5, "end": 10}],
        )

    def test_same_duration_reorder_invalidates_cuts_and_rejects_stale_save(self):
        payload = self.payload()
        self.assertEqual(
            self.client.patch(self.url, payload, format="json").status_code, 200
        )
        self.first.position = 3
        self.first.save()
        self.second.position = 1
        self.second.save()
        self.first.position = 2
        self.first.save()
        preview = self.client.get(self.preview_url).data
        self.assertTrue(preview["cuts_stale"])
        self.assertNotEqual(preview["cut_source"]["key"], payload["source_key"])
        self.assertEqual(
            preview["playback_sections"],
            [{"start": 0, "end": 5}, {"start": 5, "end": 10}],
        )
        self.video.refresh_from_db()
        self.assertEqual(
            self.client.patch(
                self.url, {**payload, "previous": self.video.cuts}, format="json"
            ).status_code,
            409,
        )

    def test_validates_ranges_ownership_and_processing(self):
        payload = self.payload()
        for sections in (
            [],
            [{"start": 0, "end": 11}],
            [{"start": 4, "end": 3}],
            [{"start": 0, "end": 3}, {"start": 2, "end": 4}],
            [{"start": "NaN", "end": 3}],
        ):
            response = self.client.patch(
                self.url, {**payload, "sections": sections}, format="json"
            )
            self.assertEqual(response.status_code, 400, response.data)
        for state in ("GENERATION", "RENDERING", "REVIEW"):
            self.video.status = state
            self.video.save()
            self.assertEqual(
                self.client.patch(self.url, payload, format="json").status_code, 409
            )
        self.client.force_authenticate(user=user.make())
        self.assertEqual(
            self.client.patch(self.url, payload, format="json").status_code, 404
        )

    def test_full_video_cut_removes_deleted_words_from_preview_and_subtitles(self):
        video = self.video_for(video_type="MANUAL", settings={"narration": False, "subtitles": True})
        scene.make(video=video, text="Hello wrong world", audio_settings={"duration": 3})
        preview_url = reverse("video-preview", args=[video.pk])
        source = self.client.get(preview_url).data["cut_source"]
        response = self.client.patch(reverse("video-cuts", args=[video.pk]), {
            "source_duration": source["duration"], "source_key": source["key"], "previous": {},
            "sections": [{"start": 0, "end": 1}, {"start": 2, "end": 3}],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        preview = self.client.get(preview_url).data
        self.assertEqual([cue["text"] for cue in preview["captions"]], ["Hello", "world"])
        self.assertEqual([word["text"] for word in preview["caption_words"]], ["Hello", "wrong", "world"])
        text = self.client.get(reverse("video-subtitles", args=[video.pk])).content.decode()
        self.assertNotIn("wrong", text)
        self.assertIn("00:00:00,000 --> 00:00:01,000\nHello", text)
        self.assertIn("00:00:01,000 --> 00:00:02,000\nworld", text)

    def test_split_without_removing_footage_does_not_repeat_subtitle_phrases(self):
        video = self.video_for(video_type="MANUAL", settings={"narration": False, "subtitles": True})
        scene.make(video=video, text="Hello wrong world", audio_settings={"duration": 3})
        source = self.client.get(reverse("video-preview", args=[video.pk])).data["cut_source"]
        response = self.client.patch(reverse("video-cuts", args=[video.pk]), {
            "source_duration": source["duration"], "source_key": source["key"], "previous": {},
            "sections": [{"start": 0, "end": 0.5}, {"start": 0.5, "end": 3}],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        text = self.client.get(reverse("video-subtitles", args=[video.pk])).content.decode()
        self.assertEqual(text, "1\n00:00:00,000 --> 00:00:03,000\nHello wrong world\n")
