"""Bound database work on frequently used editor and resource reads."""

from django.urls import reverse

from apps.apikeysmanagement.baker_recipes import api_keys
from apps.apikeysmanagement.models import ApiKeys
from apps.usermanagement.baker_recipes import user

from ...baker_recipes import avatar, scene, scene_image, voice_model
from .base import ApiTestCase


class ResourceReadQueryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user.use_service_api_keys = False
        self.user.save(update_fields=["use_service_api_keys"])
        api_keys.make(
            user=self.user, openai_key="test-openai", elevenlabs_key="test-xi"
        )

    def test_voice_list_reads_personal_keys_once_before_counting_and_fetching(self):
        shared = voice_model.make(created_by=None)
        with self.assertNumQueries(3):
            response = self.client.get(reverse("voicemodel-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [str(shared.pk)]
        )

    def test_avatar_list_does_not_read_credentials_or_query_each_voice(self):
        owned = avatar.make(created_by=self.user, _quantity=20)
        avatar.make(created_by=user.make())
        with self.assertNumQueries(2):
            response = self.client.get(reverse("avatar-list"))
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            [row["id"] for row in response.data["results"]],
            [str(row.pk) for row in owned],
        )
        self.assertTrue(all(row["sample"] for row in response.data["results"]))

    def test_avatar_voice_validation_still_rejects_unavailable_providers(self):
        presenter = avatar.make(created_by=self.user)
        unavailable = voice_model.make(provider="SIXTYDB", created_by=None)
        response = self.client.patch(
            reverse("avatar-detail", args=[presenter.pk]),
            {"voice": str(unavailable.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("voice", response.data)

    def test_voice_choices_follow_key_changes_on_the_same_authenticated_user(self):
        voice_model.make(created_by=None)
        url = reverse("voicemodel-list")
        self.assertEqual(self.client.get(url).data["count"], 1)
        ApiKeys.objects.filter(user=self.user).update(openai_key="")
        self.assertEqual(self.client.get(url).data["count"], 0)


class EditorReadQueryTests(ApiTestCase):
    def test_detail_and_preview_use_three_queries_regardless_of_scene_count(self):
        for count in (2, 20):
            video = self.video_for(settings={"narration": False})
            for row in scene.make(video=video, _quantity=count):
                scene_image.make(scene=row)
            for action in ("detail", "preview"):
                with self.subTest(scene_count=count, action=action):
                    with self.assertNumQueries(3):
                        response = self.client.get(
                            reverse(f"video-{action}", args=[video.pk])
                        )
                    self.assertEqual(response.status_code, 200)
                    rows = response.data["scenes" if action == "detail" else "segments"]
                    self.assertEqual(len(rows), count)
