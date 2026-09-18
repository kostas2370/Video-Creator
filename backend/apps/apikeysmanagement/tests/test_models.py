from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test import TestCase, override_settings
from model_bakery import baker

from ..models import ApiKeys, Provider


class EncryptionTests(TestCase):
    def test_the_key_is_not_readable_in_the_table(self):
        keys = baker.make_recipe(
            "apikeysmanagement.api_keys", openai_key="sk-super-secret"
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT openai_key FROM apikeysmanagement_apikeys WHERE id = %s",
                [keys.pk],
            )
            stored = cursor.fetchone()[0]

        self.assertNotIn("sk-super-secret", stored)

    def test_the_key_comes_back_intact(self):
        keys = baker.make_recipe(
            "apikeysmanagement.api_keys", openai_key="sk-super-secret"
        )

        self.assertEqual(
            ApiKeys.objects.get(pk=keys.pk).openai_key, "sk-super-secret"
        )

    def test_two_users_with_the_same_key_do_not_store_the_same_bytes(self):
        """Fernet salts every token, so identical keys are not correlatable in a dump."""
        first = baker.make_recipe("apikeysmanagement.api_keys", openai_key="sk-same")
        second = baker.make_recipe("apikeysmanagement.api_keys", openai_key="sk-same")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT openai_key FROM apikeysmanagement_apikeys WHERE id IN (%s, %s)",
                [first.pk, second.pk],
            )
            stored = [row[0] for row in cursor.fetchall()]

        self.assertNotEqual(stored[0], stored[1])


@override_settings(OPEN_API_KEY="service-openai-key", XI_API_KEY="service-xi-key")
class KeyForTests(TestCase):
    def setUp(self):
        self.keys = baker.make_recipe(
            "apikeysmanagement.api_keys",
            openai_key="sk-mine",
            elevenlabs_key="",
        )
        self.user = self.keys.user

    def opted_out(self):
        self.user.use_service_api_keys = False
        self.user.save(update_fields=["use_service_api_keys"])
        return self.user

    def test_uses_the_service_key_while_the_flag_is_on(self):
        self.assertTrue(self.user.use_service_api_keys)
        self.assertEqual(
            ApiKeys.key_for(self.user, Provider.OPENAI), "service-openai-key"
        )

    def test_uses_the_users_own_key_once_they_opt_out(self):
        self.assertEqual(ApiKeys.key_for(self.opted_out(), Provider.OPENAI), "sk-mine")

    def test_does_not_fall_back_to_the_service_for_a_provider_left_blank(self):
        self.assertIsNone(ApiKeys.key_for(self.opted_out(), Provider.ELEVENLABS))

    def test_is_nothing_for_an_opted_out_user_with_no_keys_at_all(self):
        stranger = baker.make_recipe(
            "usermanagement.user", use_service_api_keys=False
        )

        self.assertIsNone(ApiKeys.key_for(stranger, Provider.OPENAI))

    def test_uses_the_service_key_for_a_user_who_saved_nothing(self):
        stranger = baker.make_recipe("usermanagement.user")

        self.assertEqual(
            ApiKeys.key_for(stranger, Provider.OPENAI), "service-openai-key"
        )

    def test_gives_a_signed_out_caller_nothing(self):
        # Not even the service key: there is no account to bill it to.
        self.assertIsNone(ApiKeys.key_for(AnonymousUser(), Provider.OPENAI))

    def test_gives_an_internal_caller_the_service_key(self):
        # No user at all is a management command or a script, not a signed-out person.
        self.assertEqual(
            ApiKeys.key_for(None, Provider.OPENAI), "service-openai-key"
        )

    @override_settings(OPEN_API_KEY="")
    def test_is_nothing_when_the_service_has_no_key_either(self):
        stranger = baker.make_recipe("usermanagement.user")

        self.assertIsNone(ApiKeys.key_for(stranger, Provider.OPENAI))

    def test_every_provider_maps_to_a_column_that_exists(self):
        for provider, (field, _) in ApiKeys.FIELDS.items():
            with self.subTest(provider=provider):
                self.assertTrue(hasattr(self.keys, field))

        self.assertEqual(len(ApiKeys.FIELDS), len(Provider.choices))


class MaskTests(TestCase):
    def test_shows_only_the_ends_of_a_long_key(self):
        self.assertEqual(ApiKeys.mask("sk-abcdefghijkl"), "sk-••••••••ijkl")

    def test_hides_a_short_key_outright(self):
        self.assertEqual(ApiKeys.mask("sk-short"), "••••••••")

    def test_is_empty_for_a_provider_with_no_key(self):
        self.assertEqual(ApiKeys.mask(""), "")
        self.assertEqual(ApiKeys.mask(None), "")
