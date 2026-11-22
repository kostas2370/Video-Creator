from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.apikeysmanagement.baker_recipes import api_keys
from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.apikeysmanagement.provider_requests import key_request
from apps.usermanagement.baker_recipes import user
from apps.usermanagement.models import User
from apps.usermanagement.serializers import RegisterSerializer
from apps.videomanagement.models import Avatar
from apps.videomanagement.baker_recipes import voice_model
from apps.videomanagement.models import VoiceModel
from apps.videomanagement.services.media.selection import owned_asset
from apps.videomanagement.services.voices.credentials import key_source
from apps.videomanagement.utils.composer.render import avatar_source


@override_settings(SERVICE_API_KEYS_ENABLED=False, SADTALKER_ENABLED=False)
class BetaPolicyTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.owner = user.make(use_service_api_keys=True)
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    @override_settings(OPEN_API_KEY="shared-key-must-not-be-used")
    def test_existing_service_accounts_use_only_their_own_keys(self):
        api_keys.make(user=self.owner, openai_key="personal-openai", elevenlabs_key="")
        self.assertFalse(self.owner.uses_service_api_keys)
        self.assertEqual(
            ApiKeys.key_for(self.owner, Provider.OPENAI), "personal-openai"
        )
        self.assertIsNone(ApiKeys.key_for(self.owner, Provider.ELEVENLABS))
        self.assertIsNone(ApiKeys.key_for(None, Provider.OPENAI))
        self.assertEqual(key_source(self.owner), "user")

    @override_settings(OPEN_API_KEY="shared-key-must-not-be-used")
    def test_missing_personal_keys_never_fall_back_to_shared_keys(self):
        self.assertIsNone(ApiKeys.key_for(self.owner, Provider.OPENAI))
        self.assertFalse(User().use_service_api_keys)

    def test_missing_account_keys_block_sdk_environment_fallbacks(self):
        with self.assertRaises(ValidationError):
            with key_request(self.owner, Provider.OPENAI):
                self.fail("No provider client should be created without an account key")
        with self.assertRaises(ValidationError):
            with key_request(None, Provider.OPENAI, api_key="stale-shared-key"):
                self.fail("An internal caller must not use a shared key")

    def test_sdk_calls_use_the_current_personal_key_instead_of_stale_credentials(self):
        api_keys.make(user=self.owner, openai_key="current-personal-key")
        with key_request(
            self.owner, Provider.OPENAI, api_key="stale-shared-key"
        ) as key:
            self.assertEqual(key, "current-personal-key")

    def test_settings_report_the_effective_policy_and_reject_service_mode(self):
        response = self.client.get(reverse("api-keys"))
        self.assertFalse(response.data["use_service_api_keys"])
        self.assertFalse(response.data["service_keys_allowed"])
        response = self.client.patch(
            reverse("api-keys"), {"use_service_api_keys": True}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_existing_service_accounts_see_their_personal_account_voices(self):
        api_keys.make(user=self.owner, elevenlabs_key="personal-elevenlabs")
        personal = voice_model.make(created_by=self.owner, provider=Provider.ELEVENLABS)
        shared = voice_model.make(created_by=None, provider=Provider.ELEVENLABS)
        available = VoiceModel.objects.available_to(self.owner)
        self.assertTrue(available.filter(pk=personal.pk).exists())
        self.assertFalse(available.filter(pk=shared.pk).exists())

    def test_personal_keys_can_still_be_saved_and_are_masked(self):
        response = self.client.patch(
            reverse("api-keys"),
            {"openai_key": "sk-personal-provider-key"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("sk-personal-provider-key", str(response.data))
        self.assertEqual(
            ApiKeys.key_for(self.owner, Provider.OPENAI), "sk-personal-provider-key"
        )

    def test_public_policy_contains_only_feature_flags(self):
        self.client.force_authenticate(None)
        response = self.client.get(reverse("deployment"))
        self.assertEqual(
            response.data,
            {
                "sadtalker_enabled": False,
                "service_keys_allowed": False,
                "invite_only": False,
            },
        )
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_presenter_asset_requests_are_blocked(self):
        for method in (self.client.get, self.client.post):
            self.assertEqual(method("/api/avatars/").status_code, 404)
        with self.assertRaises(ValidationError):
            owned_asset(Avatar, "saved-presenter", self.owner)
        self.assertIsNone(owned_asset(Avatar, "", self.owner))

    def test_saved_presenters_do_not_load_models_during_render(self):
        self.assertIsNone(avatar_source(SimpleNamespace(avatar=object())))

    @patch("apps.videomanagement.management.commands.setup_checkpoints.gdown")
    def test_disabled_presenters_do_not_download_checkpoints(self, download):
        output = StringIO()
        call_command("setup_checkpoints", stdout=output)
        download.download.assert_not_called()
        self.assertIn("skipping model downloads", output.getvalue())

    @override_settings(SIGNUP_ALLOWED_EMAILS=("invited@example.com",))
    def test_signup_requires_an_invited_email(self):
        serializer = RegisterSerializer()
        self.assertEqual(
            serializer.validate_email("Invited@Example.com"), "Invited@Example.com"
        )
        with self.assertRaises(ValidationError):
            serializer.validate_email("stranger@example.com")

    @override_settings(SIGNUP_ALLOWED_EMAILS=())
    def test_empty_invitation_list_closes_registration(self):
        with self.assertRaises(ValidationError):
            RegisterSerializer().validate_email("anyone@example.com")

    def test_registration_is_limited_even_when_validation_fails(self):
        self.client.force_authenticate(None)
        for _ in range(5):
            self.assertEqual(
                self.client.post(reverse("register"), {}, format="json").status_code,
                400,
            )
        self.assertEqual(
            self.client.post(reverse("register"), {}, format="json").status_code, 429
        )
