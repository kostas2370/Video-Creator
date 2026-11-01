from django.urls import reverse

from apps.usermanagement.baker_recipes import user
from apps.usage.models import AIUsage, GenerationEstimate
from apps.usage.services import record_usage, video_usage
from apps.videomanagement.baker_recipes import scene
from apps.videomanagement.models import Video

from .base import ApiTestCase


class DraftDeletionTests(ApiTestCase):
    def test_review_draft_can_be_deleted_from_the_library(self):
        draft = self.video_for(status="REVIEW")
        self.assertEqual(
            self.client.delete(reverse("video-detail", args=[draft.pk])).status_code,
            204,
        )
        self.assertFalse(Video.objects.filter(pk=draft.pk).exists())

    def test_draft_action_deletes_reviewed_draft_and_keeps_usage_history(self):
        draft = self.video_for(status="REVIEW")
        GenerationEstimate.objects.create(video=draft, estimate={})
        with video_usage(draft):
            record_usage(
                self.user,
                "text",
                "OPENAI",
                "gpt-5.4-mini",
                {"input_tokens": 100, "output_tokens": 200},
            )
        self.assertEqual(
            self.client.delete(
                reverse("video-discard-draft", args=[draft.pk])
            ).status_code,
            204,
        )
        self.assertFalse(Video.objects.filter(pk=draft.pk).exists())
        self.assertFalse(GenerationEstimate.objects.exists())
        self.assertIsNone(AIUsage.objects.get().video_id)
        self.assertIsNotNone(AIUsage.objects.get().cost_usd)

    def test_active_generation_and_exports_cannot_be_deleted(self):
        for status in ("GENERATION", "RENDERING"):
            for route in ("video-detail", "video-discard-draft"):
                with self.subTest(status=status, route=route):
                    draft = self.video_for(status=status)
                    self.assertEqual(
                        self.client.delete(reverse(route, args=[draft.pk])).status_code,
                        409,
                    )
                    self.assertTrue(Video.objects.filter(pk=draft.pk).exists())

    def test_stale_draft_action_cannot_delete_a_project_that_has_progressed(self):
        for status in ("READY", "COMPLETED"):
            draft = self.video_for(status=status)
            self.assertEqual(
                self.client.delete(
                    reverse("video-discard-draft", args=[draft.pk])
                ).status_code,
                409,
            )
            self.assertTrue(Video.objects.filter(pk=draft.pk).exists())

    def test_failed_empty_drafts_can_be_deleted_but_prepared_projects_are_preserved(
        self,
    ):
        empty = self.video_for(status="FAILED")
        prepared = self.video_for(status="FAILED")
        scene.make(video=prepared)
        self.assertEqual(
            self.client.delete(
                reverse("video-discard-draft", args=[empty.pk])
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.delete(
                reverse("video-discard-draft", args=[prepared.pk])
            ).status_code,
            409,
        )

    def test_deletion_is_private_and_requires_authentication(self):
        draft = self.video_for(owner=user.make(), status="REVIEW")
        for route in ("video-detail", "video-discard-draft"):
            self.assertEqual(
                self.client.delete(reverse(route, args=[draft.pk])).status_code, 404
            )
        self.client.force_authenticate(None)
        self.assertIn(
            self.client.delete(
                reverse("video-discard-draft", args=[draft.pk])
            ).status_code,
            (401, 403),
        )
        self.assertTrue(Video.objects.filter(pk=draft.pk).exists())
