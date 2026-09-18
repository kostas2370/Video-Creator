from unittest.mock import patch

from django.test import TestCase
from model_bakery import baker
from rest_framework.test import APIClient

from apps.videomanagement.models import VoiceModel

from ..models import ApiKeys, Provider
from ..tasks import import_user_voices

URL = "/api/api_keys/"


class ImportUserVoicesTests(TestCase):
    def setUp(self):
        self.user = baker.make_recipe("usermanagement.user")

    def labs_returns(self, *voices):
        return patch(
            "apps.videomanagement.utils.gpt_utils.get_voices_from_labs",
            return_value=list(voices),
        )

    def test_imports_the_voices_against_the_user_who_owns_the_key(self):
        with self.labs_returns(
            {"name": "Rachel", "voice_id": "abc", "preview_url": "https://a.test/x"}
        ):
            added = import_user_voices(self.user.id, Provider.ELEVENLABS)

        voice = VoiceModel.objects.get(path="abc")
        self.assertEqual(added, 1)
        self.assertEqual(voice.created_by, self.user)
        self.assertEqual(voice.provider, "eleven_labs")
        self.assertEqual(voice.type, "API")

    def test_running_it_twice_does_not_duplicate_anything(self):
        voices = [{"name": "Rachel", "voice_id": "abc", "preview_url": ""}]

        with self.labs_returns(*voices):
            import_user_voices(self.user.id, Provider.ELEVENLABS)
            added = import_user_voices(self.user.id, Provider.ELEVENLABS)

        self.assertEqual(added, 0)
        self.assertEqual(VoiceModel.objects.filter(path="abc").count(), 1)

    def test_two_users_can_hold_a_voice_of_the_same_name(self):
        stranger = baker.make_recipe("usermanagement.user")
        voices = [{"name": "Rachel", "voice_id": "abc", "preview_url": ""}]

        with self.labs_returns(*voices):
            import_user_voices(self.user.id, Provider.ELEVENLABS)
            import_user_voices(stranger.id, Provider.ELEVENLABS)

        self.assertEqual(VoiceModel.objects.filter(name="Rachel").count(), 2)

    def test_does_nothing_for_a_user_who_no_longer_exists(self):
        self.assertEqual(import_user_voices(999999, Provider.ELEVENLABS), 0)


class KeySaveTriggersImportTests(TestCase):
    def setUp(self):
        self.user = baker.make_recipe("usermanagement.user")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def patch_keys(self, **payload):
        with patch("apps.apikeysmanagement.signals.import_user_voices") as import_task:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.patch(URL, payload, format="json")

        return import_task

    def test_saving_an_elevenlabs_key_queues_the_import(self):
        import_task = self.patch_keys(elevenlabs_key="xi-key")

        import_task.delay.assert_called_once_with(self.user.id, Provider.ELEVENLABS)

    def test_saving_a_60db_key_queues_its_own_import(self):
        import_task = self.patch_keys(sixtydb_key="60db-key")

        import_task.delay.assert_called_once_with(self.user.id, Provider.SIXTYDB)

    def test_saving_an_unrelated_key_queues_nothing(self):
        import_task = self.patch_keys(openai_key="sk-key")

        import_task.delay.assert_not_called()

    def test_clearing_the_key_queues_nothing(self):
        baker.make_recipe(
            "apikeysmanagement.api_keys", user=self.user, elevenlabs_key="xi-key"
        )

        import_task = self.patch_keys(elevenlabs_key="")

        import_task.delay.assert_not_called()

    def test_saving_the_same_key_again_does_not_re_import(self):
        baker.make_recipe(
            "apikeysmanagement.api_keys", user=self.user, elevenlabs_key="xi-key"
        )

        import_task = self.patch_keys(elevenlabs_key="xi-key")

        import_task.delay.assert_not_called()

    def test_fires_for_a_key_saved_outside_the_api(self):
        keys = baker.make_recipe("apikeysmanagement.api_keys", user=self.user)

        with patch("apps.apikeysmanagement.signals.import_user_voices") as import_task:
            with self.captureOnCommitCallbacks(execute=True):
                keys.elevenlabs_key = "xi-typed-in-the-admin"
                keys.save()

        import_task.delay.assert_called_once_with(self.user.id, Provider.ELEVENLABS)

    def test_fires_when_the_row_is_created_with_a_key_already_on_it(self):
        with patch("apps.apikeysmanagement.signals.import_user_voices") as import_task:
            with self.captureOnCommitCallbacks(execute=True):
                ApiKeys.objects.create(user=self.user, elevenlabs_key="xi-key")

        import_task.delay.assert_called_once_with(self.user.id, Provider.ELEVENLABS)
