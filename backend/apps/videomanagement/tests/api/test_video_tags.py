import json
from unittest.mock import patch

from django.urls import reverse
from rest_framework.exceptions import APIException

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import scene
from ...models import Video
from .base import ApiTestCase

TAGS = {
    "tiktok": ["OceanLife", "Nature"],
    "youtube": ["ocean life", "marine animals"],
    "search": ["ocean", "wildlife"],
}
MODEL = "apps.videomanagement.services.videos.tags.get_update_sentence"


class VideoTagsTests(ApiTestCase):
    def generate(self, video, previous=None):
        return self.client.post(
            reverse("video-generate-tags", args=[video.pk]),
            {"previous_tags": previous or {}},
            format="json",
        )

    def save_tags(self, video, tags, previous=None):
        return self.client.patch(
            reverse("video-tags", args=[video.pk]),
            {"tags": tags, "previous_tags": previous or {}},
            format="json",
        )

    def test_generate_uses_edited_content_and_preserves_render_state(self):
        video = self.video_for(
            title="Ocean life",
            status="COMPLETED",
            gpt_answer={"title": "Old", "scenes": [{"scene": "Old script"}]},
        )
        scene.make(video=video, text="Whales migrate across the ocean.")
        original_time, original_settings = video.updated_at, video.settings.copy()
        with patch(MODEL, return_value=json.dumps(TAGS)) as generate:
            response = self.generate(video)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["tags"], TAGS)
        self.assertIn("Whales migrate", generate.call_args.args[0])
        self.assertNotIn("Old script", generate.call_args.args[0])
        self.assertEqual(generate.call_args.kwargs["user"], self.user)
        video.refresh_from_db()
        self.assertEqual(video.tags, TAGS)
        self.assertEqual(video.status, "COMPLETED")
        self.assertEqual(video.updated_at, original_time)
        self.assertEqual(video.settings, original_settings)
        self.assertEqual(
            self.client.get(reverse("video-detail", args=[video.pk])).data["tags"], TAGS
        )
        self.scene_queue.assert_not_called()

    def test_english_fenced_json_normalization_and_duplicate_removal(self):
        video = self.video_for()
        tags = {
            "tiktok": ["#Nature", "nature", "Ocean Life"],
            "youtube": ["  sea   life ", "Sea life"],
            "search": ["nature", "Nature"],
        }
        with patch(MODEL, return_value="```json\n" + json.dumps(tags) + "\n```"):
            response = self.generate(video)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data["tags"],
            {
                "tiktok": ["Nature", "OceanLife"],
                "youtube": ["sea life"],
                "search": ["nature"],
            },
        )

    def test_non_english_source_still_requests_english_discovery_tags(self):
        video = self.video_for(title="Η ζωή στον ωκεανό")
        scene.make(video=video, text="Οι φάλαινες ταξιδεύουν στον ωκεανό.")
        with patch(MODEL, return_value=json.dumps(TAGS)) as generate:
            response = self.generate(video)
        self.assertEqual(response.status_code, 200)
        prompt = generate.call_args.args[0]
        self.assertIn("Write ALL tags in English", prompt)
        self.assertIn("viewer search intent", prompt)
        self.assertIn("long-tail searches", prompt)
        self.assertIn("Οι φάλαινες", prompt)
        self.assertEqual(response.data["tags"], TAGS)

    def test_non_english_output_is_retried_without_saving_it(self):
        video = self.video_for(tags=TAGS)
        foreign = {
            "tiktok": ["Φύση"],
            "youtube": ["θαλάσσια ζωή"],
            "search": ["ωκεανός"],
        }
        with patch(
            MODEL, side_effect=[json.dumps(foreign), json.dumps(TAGS)]
        ) as generate:
            response = self.generate(video, TAGS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(generate.call_count, 2)
        self.assertIn("translate rather than copying", generate.call_args.args[0])
        with patch(MODEL, return_value=json.dumps(foreign)) as generate:
            response = self.generate(video, TAGS)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(generate.call_count, 2)
        self.assertIn("English tags", str(response.data))
        video.refresh_from_db()
        self.assertEqual(video.tags, TAGS)

    def test_manual_tags_clear_and_save_while_rendering(self):
        video = self.video_for(status="RENDERING")
        self.assertEqual(self.save_tags(video, TAGS).status_code, 200)
        empty = {"tiktok": [], "youtube": [], "search": []}
        self.assertEqual(self.save_tags(video, empty, TAGS).status_code, 200)
        video.refresh_from_db()
        self.assertEqual(video.tags, empty)
        self.assertEqual(video.status, "RENDERING")

    def test_invalid_tags_do_not_overwrite_saved_metadata(self):
        video = self.video_for(tags=TAGS)
        for tags in (
            {},
            [],
            {**TAGS, "tiktok": "ocean"},
            {**TAGS, "search": ["x" * 81]},
            {**TAGS, "youtube": [f"word {index}" for index in range(21)]},
            {**TAGS, "tiktok": ["!!!"]},
            {**TAGS, "search": [""]},
            {**TAGS, "search": [123]},
            {**TAGS, "youtube": ["a,b"]},
        ):
            with self.subTest(tags=tags):
                self.assertEqual(self.save_tags(video, tags, TAGS).status_code, 400)
        video.refresh_from_db()
        self.assertEqual(video.tags, TAGS)

    def test_invalid_ai_reply_and_provider_errors_preserve_tags(self):
        video = self.video_for(tags=TAGS)
        for reply in (
            "not json",
            "[]",
            "null",
            "{}",
            json.dumps({**TAGS, "youtube": []}),
        ):
            with self.subTest(reply=reply), patch(MODEL, return_value=reply):
                response = self.generate(video, TAGS)
            self.assertEqual(response.status_code, 500)
            self.assertIn("invalid tags", str(response.data))
        with patch(MODEL, side_effect=APIException("Provider unavailable")):
            self.assertEqual(self.generate(video, TAGS).status_code, 500)
        video.refresh_from_db()
        self.assertEqual(video.tags, TAGS)

    def test_stale_saves_and_generation_cannot_replace_newer_tags(self):
        video = self.video_for(tags=TAGS)
        with patch(MODEL) as generate:
            self.assertEqual(self.generate(video).status_code, 409)
        generate.assert_not_called()
        empty = {"tiktok": [], "youtube": [], "search": []}
        self.assertEqual(self.save_tags(video, empty).status_code, 409)
        self.assertEqual(self.save_tags(video, TAGS).status_code, 200)

        def other_session(*args, **kwargs):
            Video.objects.filter(pk=video.pk).update(tags=empty)
            return json.dumps(TAGS)

        with patch(MODEL, side_effect=other_session):
            self.assertEqual(self.generate(video, TAGS).status_code, 409)
        video.refresh_from_db()
        self.assertEqual(video.tags, empty)

    def test_search_finds_each_tag_group_without_exposing_foreign_videos(self):
        video = self.video_for(title="Different title", tags=TAGS)
        self.video_for(owner=user.make(), tags=TAGS)
        for term in ("ocean", "Nature", "marine animals", "wildlife", "Different"):
            response = self.client.get(reverse("video-list"), {"search": term})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                [item["id"] for item in response.data["results"]], [str(video.pk)]
            )
        self.assertEqual(
            self.client.get(reverse("video-list"), {"search": "unrelated"}).data[
                "count"
            ],
            0,
        )

    def test_ownership_authentication_and_validation_precede_provider_calls(self):
        video = self.video_for(owner=user.make())
        with patch(MODEL) as generate:
            self.assertEqual(self.generate(video).status_code, 404)
            self.assertEqual(self.save_tags(video, TAGS).status_code, 404)
            owned = self.video_for()
            self.assertEqual(
                self.client.post(
                    reverse("video-generate-tags", args=[owned.pk]), {}, format="json"
                ).status_code,
                400,
            )
            self.client.force_authenticate(None)
            self.assertIn(self.generate(owned).status_code, (401, 403))
            self.assertIn(self.save_tags(owned, TAGS).status_code, (401, 403))
        generate.assert_not_called()

    def test_generation_can_use_storyboard_or_prompt_before_scenes_exist(self):
        for video in (
            self.video_for(gpt_answer={"scenes": [{"scene": "A whale surfaces"}]}),
            self.video_for(gpt_answer=None),
        ):
            with patch(MODEL, return_value=json.dumps(TAGS)) as generate:
                self.assertEqual(self.generate(video).status_code, 200)
            self.assertIn(
                "A whale surfaces" if video.gpt_answer else video.prompt.prompt,
                generate.call_args.args[0],
            )
