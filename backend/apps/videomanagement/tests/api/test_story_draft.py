import json
from unittest.mock import patch

from django.urls import reverse
from rest_framework.exceptions import APIException

from ...models import Video
from .base import ApiTestCase


class StoryDraftTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("video-draft-story")

    def test_generates_an_editable_draft_without_creating_a_video_or_audio(self):
        draft = {"title": "The wrong number", "story": "The text arrived at midnight. It was from my future self."}
        with patch("apps.videomanagement.services.story.get_update_sentence", return_value=json.dumps(draft)) as generate:
            response = self.client.post(self.url, {"prompt": "A mysterious text message"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, draft)
        self.assertEqual(generate.call_args.kwargs["user"], self.user)
        self.assertIn("A mysterious text message", generate.call_args.args[0])
        self.assertFalse(Video.objects.exists())
        self.scene_queue.assert_not_called()

    def test_accepts_fenced_json_and_unicode(self):
        draft = {"title": "Ένα μήνυμα", "story": "Το μήνυμα ήρθε τα μεσάνυχτα."}
        with patch("apps.videomanagement.services.story.get_update_sentence", return_value="```json\n" + json.dumps(draft) + "\n```"):
            response = self.client.post(self.url, {"prompt": "Μια ελληνική ιστορία"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, draft)

    def test_invalid_input_is_rejected_before_the_model_call(self):
        with patch("apps.videomanagement.services.story.get_update_sentence") as generate:
            for prompt in ("", " ", "a" * 2001):
                self.assertEqual(self.client.post(self.url, {"prompt": prompt}, format="json").status_code, 400)
        generate.assert_not_called()

    def test_invalid_model_output_never_reaches_the_editor(self):
        for reply in ("not json", "[]", '{"title": "Title"}', json.dumps({"title": "Title", "story": "x" * 2001})):
            with self.subTest(reply=reply[:30]), patch("apps.videomanagement.services.story.get_update_sentence", return_value=reply):
                response = self.client.post(self.url, {"prompt": "A mystery"}, format="json")
                self.assertEqual(response.status_code, 500)
                self.assertIn("invalid story draft", str(response.data))
        self.assertFalse(Video.objects.exists())

    def test_provider_failure_and_unauthenticated_requests(self):
        with patch("apps.videomanagement.services.story.get_update_sentence", side_effect=APIException("Text provider unavailable")):
            response = self.client.post(self.url, {"prompt": "A mystery"}, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertIn("Text provider unavailable", str(response.data))
        self.client.force_authenticate(None)
        with patch("apps.videomanagement.services.story.get_update_sentence") as generate:
            self.assertIn(self.client.post(self.url, {"prompt": "A mystery"}, format="json").status_code, (401, 403))
        generate.assert_not_called()
