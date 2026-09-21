import json

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.usermanagement.baker_recipes import user

from ..baker_recipes import api_keys
from ..models import ApiKeys


class ApiKeysViewTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_a_user_who_never_saved_a_key_gets_an_empty_set_back(self):
        response = self.client.get(reverse("api-keys"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["openai_key"], "")
        self.assertTrue(ApiKeys.objects.filter(user=self.user).exists())

    def test_saves_a_key_and_answers_with_it_masked(self):
        response = self.client.patch(
            reverse("api-keys"), {"openai_key": "sk-abcdefghijkl"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["openai_key"], "sk-••••••••ijkl")
        self.assertEqual(
            ApiKeys.objects.get(user=self.user).openai_key, "sk-abcdefghijkl"
        )

    def test_never_writes_the_key_itself_into_a_response(self):
        self.client.patch(
            reverse("api-keys"), {"openai_key": "sk-abcdefghijkl"}, format="json"
        )

        body = json.dumps(self.client.get(reverse("api-keys")).data)

        self.assertNotIn("sk-abcdefghijkl", body)

    def test_leaves_the_other_providers_alone(self):
        api_keys.make(
            user=self.user,
            elevenlabs_key="keep-me-please",
        )

        self.client.patch(
            reverse("api-keys"), {"openai_key": "sk-abcdefghijkl"}, format="json"
        )

        self.assertEqual(
            ApiKeys.objects.get(user=self.user).elevenlabs_key, "keep-me-please"
        )

    def test_an_empty_string_clears_a_key(self):
        api_keys.make(user=self.user, openai_key="sk-old")

        self.client.patch(reverse("api-keys"), {"openai_key": ""}, format="json")

        self.assertEqual(ApiKeys.objects.get(user=self.user).openai_key, "")

    def test_deleting_clears_every_provider(self):
        api_keys.make(user=self.user)

        response = self.client.delete(reverse("api-keys"))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ApiKeys.objects.filter(user=self.user).exists())

    def test_one_user_can_never_reach_another_users_keys(self):
        stranger = user.make()
        api_keys.make(user=stranger, openai_key="sk-theirs")

        self.client.patch(reverse("api-keys"), {"openai_key": "sk-mine"}, format="json")

        self.assertEqual(ApiKeys.objects.get(user=stranger).openai_key, "sk-theirs")
        self.assertEqual(ApiKeys.objects.get(user=self.user).openai_key, "sk-mine")

    def test_toggles_which_keys_the_pipeline_spends(self):
        response = self.client.patch(
            reverse("api-keys"), {"use_service_api_keys": False}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIs(response.data["use_service_api_keys"], False)
        self.user.refresh_from_db()
        self.assertFalse(self.user.use_service_api_keys)

    def test_is_closed_to_anyone_not_signed_in(self):
        self.client.force_authenticate(None)

        self.assertEqual(self.client.get(reverse("api-keys")).status_code, 401)
