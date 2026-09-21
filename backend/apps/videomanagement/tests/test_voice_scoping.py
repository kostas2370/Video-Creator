from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.apikeysmanagement.baker_recipes import api_keys
from apps.usermanagement.baker_recipes import superuser, user

from ..baker_recipes import voice_model
from ..models import VoiceModel


def a_voice(**kwargs):
    return voice_model.make(**kwargs)


class AvailableToTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.shared = a_voice(created_by=None)
        self.mine = a_voice(created_by=self.user, provider="eleven_labs")
        self.theirs = a_voice(
            created_by=user.make(),
            provider="eleven_labs",
        )

    def opted_out(self, **keys):
        api_keys.make(
            user=self.user,
            **{"openai_key": "sk-mine", "elevenlabs_key": "xi-mine", **keys},
        )
        self.user.use_service_api_keys = False
        self.user.save(update_fields=["use_service_api_keys"])
        return self.user

    def test_gives_the_shared_voices_to_everyone(self):
        self.assertIn(self.shared, VoiceModel.available_to(self.user))

    def test_keeps_the_shared_voices_once_you_spend_your_own_keys(self):
        self.assertIn(self.shared, VoiceModel.available_to(self.opted_out()))

    def test_keeps_the_openai_voices_the_fixtures_ship(self):
        alloy = a_voice(created_by=None, provider="open_ai", name="alloy", path="alloy")

        self.assertIn(alloy, VoiceModel.available_to(self.user))
        self.assertIn(alloy, VoiceModel.available_to(self.opted_out()))

    def test_never_gives_one_users_voice_to_another(self):
        self.assertNotIn(self.theirs, VoiceModel.available_to(self.opted_out()))

    def test_adds_your_own_voices_once_you_spend_your_own_keys(self):
        self.assertIn(self.mine, VoiceModel.available_to(self.opted_out()))

    def test_hides_your_own_voices_while_the_service_keys_are_in_use(self):
        self.assertTrue(self.user.use_service_api_keys)
        self.assertNotIn(self.mine, VoiceModel.available_to(self.user))

    def test_gives_a_signed_out_caller_nothing(self):
        self.assertEqual(list(VoiceModel.available_to(None)), [self.shared])

    def test_survives_an_anonymous_caller(self):
        self.assertEqual(list(VoiceModel.available_to(AnonymousUser())), [])

    def test_select_voice_never_picks_a_voice_the_user_cannot_spend(self):
        self.theirs.delete()
        self.shared.delete()

        self.assertIsNone(VoiceModel.select_voice(self.user))


class KeyGatedVoiceTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.openai = a_voice(provider="open_ai", name="alloy", created_by=None)
        self.labs = a_voice(provider="eleven_labs", name="Rachel", created_by=None)

    def opt_out_with(self, **keys):
        api_keys.make(user=self.user, **keys)
        self.user.use_service_api_keys = False
        self.user.save(update_fields=["use_service_api_keys"])
        return self.user

    @override_settings(OPEN_API_KEY="", XI_API_KEY="service-xi")
    def test_hides_the_openai_voices_when_the_service_has_no_openai_key(self):
        visible = VoiceModel.available_to(self.user)

        self.assertNotIn(self.openai, visible)
        self.assertIn(self.labs, visible)

    def test_shows_them_once_the_service_key_is_there(self):
        self.assertIn(self.openai, VoiceModel.available_to(self.user))

    def test_hides_the_openai_voices_when_your_own_keys_have_no_openai_key(self):
        user = self.opt_out_with(openai_key="", elevenlabs_key="xi-mine")
        mine = a_voice(provider="eleven_labs", name="MyClone", created_by=user)

        visible = VoiceModel.available_to(user)

        self.assertNotIn(self.openai, visible)
        self.assertIn(mine, visible)

    @override_settings(OPEN_API_KEY="", XI_API_KEY="")
    def test_shows_the_openai_voices_when_your_own_openai_key_is_set(self):
        user = self.opt_out_with(openai_key="sk-mine", elevenlabs_key="")

        visible = VoiceModel.available_to(user)

        self.assertIn(self.openai, visible)
        self.assertNotIn(self.labs, visible)

    @override_settings(OPEN_API_KEY="", XI_API_KEY="")
    def test_your_own_key_unlocks_a_provider_the_service_cannot_reach(self):
        user = self.opt_out_with(openai_key="sk-mine", elevenlabs_key="xi-mine")
        mine = a_voice(provider="eleven_labs", name="MyClone", created_by=user)

        self.assertCountEqual(VoiceModel.available_to(user), [self.openai, mine])

    def test_hides_the_services_elevenlabs_voices_once_you_spend_your_own_keys(self):
        user = self.opt_out_with(openai_key="sk-mine", elevenlabs_key="xi-mine")

        self.assertNotIn(self.labs, VoiceModel.available_to(user))

    def test_keeps_the_services_elevenlabs_voices_while_on_the_service_keys(self):
        self.assertIn(self.labs, VoiceModel.available_to(self.user))

    def test_keeps_the_shared_openai_voices_either_way(self):
        self.assertIn(self.openai, VoiceModel.available_to(self.user))

        user = self.opt_out_with(openai_key="sk-mine")

        self.assertIn(self.openai, VoiceModel.available_to(user))

    @override_settings(OPEN_API_KEY="", XI_API_KEY="")
    def test_offers_nothing_when_no_key_reaches_any_provider(self):
        self.assertEqual(list(VoiceModel.available_to(self.user)), [])
        self.assertIsNone(VoiceModel.select_voice(self.user))

    def test_hides_a_voice_whose_provider_cannot_be_synthesised_at_all(self):
        orphan = a_voice(provider="some_dead_provider", created_by=None)

        self.assertNotIn(orphan, VoiceModel.available_to(self.user))


class VoiceViewTests(TestCase):
    def setUp(self):
        self.user = user.make()
        api_keys.make(
            user=self.user,
            openai_key="sk-mine",
            elevenlabs_key="xi-mine",
        )
        self.user.use_service_api_keys = False
        self.user.save(update_fields=["use_service_api_keys"])

        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.shared = a_voice(created_by=None)
        self.theirs = a_voice(created_by=user.make())

    def test_lists_the_shared_voices_and_your_own_only(self):
        mine = a_voice(created_by=self.user)

        ids = [
            voice["id"] for voice in self.client.get(reverse("voicemodel-list")).data
        ]

        self.assertCountEqual(ids, [self.shared.id, mine.id])

    def test_will_not_serve_another_users_voice(self):
        response = self.client.get(reverse("voicemodel-detail", args=[self.theirs.id]))

        self.assertEqual(response.status_code, 404)

    def test_will_not_let_anyone_delete_a_shared_voice(self):
        self.client.delete(reverse("voicemodel-detail", args=[self.shared.id]))

        self.assertTrue(VoiceModel.objects.filter(pk=self.shared.pk).exists())

    def test_lets_you_delete_your_own(self):
        mine = a_voice(created_by=self.user)

        response = self.client.delete(reverse("voicemodel-detail", args=[mine.id]))

        self.assertEqual(response.status_code, 204)

    @override_settings(OPEN_API_KEY="", XI_API_KEY="")
    def test_offers_a_superuser_nothing_they_have_no_key_for(self):
        admin = superuser.make()
        admin.use_service_api_keys = False
        admin.save(update_fields=["use_service_api_keys"])

        client = APIClient()
        client.force_authenticate(admin)

        self.assertEqual(client.get(reverse("voicemodel-list")).data, [])
