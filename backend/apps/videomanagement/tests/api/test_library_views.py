from django.test import override_settings
from django.urls import reverse
from unittest.mock import Mock
from ...serializers import AvatarSerializer

from apps.usermanagement.baker_recipes import superuser, user

from ...baker_recipes import avatar, intro, voice_model
from .base import ApiTestCase


class LibraryViewTests(ApiTestCase):
    """Intros, outros, avatars and voices a caller can pick from."""

    def test_each_owner_sees_only_their_own_intros_and_outros(self):
        mine = intro.make(created_by=self.user)
        intro.make(
            created_by=user.make(),
        )

        response = self.client.get(reverse("intro-list"))

        self.assertEqual([i["id"] for i in response.data], [mine.id])

    def test_a_superuser_sees_every_intro(self):
        intro.make(_quantity=2)
        self.client.force_authenticate(superuser.make())

        self.assertEqual(len(self.client.get(reverse("intro-list")).data), 2)

    def test_each_owner_sees_only_their_own_avatars(self):
        mine = avatar.make(created_by=self.user)
        avatar.make()

        response = self.client.get(reverse("avatar-list"))

        self.assertEqual([a["id"] for a in response.data], [mine.id])

    def test_voices_are_shared_by_everyone(self):
        voice_model.make(_quantity=2)

        self.assertEqual(len(self.client.get(reverse("voicemodel-list")).data), 2)

    @override_settings(OPEN_API_KEY="")
    def test_no_voices_are_offered_when_no_key_reaches_their_provider(self):
        voice_model.make(_quantity=2)

        self.assertEqual(len(self.client.get(reverse("voicemodel-list")).data), 0)

    def test_avatar_cannot_use_another_users_private_voice(self):
        foreign = voice_model.make(created_by=user.make(), type="CUSTOM_API", provider="private")
        row = avatar.make(created_by=self.user)
        serializer = AvatarSerializer(
            row, data={"voice": foreign.id}, partial=True,
            context={"request": Mock(user=self.user)},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("voice", serializer.errors)

    def test_avatar_can_use_an_owned_custom_voice(self):
        owned = voice_model.make(created_by=self.user, type="CUSTOM_API", provider="private")
        self.user.use_service_api_keys = False
        serializer = AvatarSerializer(
            avatar.make(created_by=self.user), data={"voice": owned.id}, partial=True,
            context={"request": Mock(user=self.user)},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
