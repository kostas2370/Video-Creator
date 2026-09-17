from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from model_bakery import baker
from rest_framework.test import APIRequestFactory

from ..permissions import (
    AiGenerationLimitPermission,
    IsOwnerPermission,
    SceneGenerationLimitPermission,
    SceneImageGenerationLimitPermission,
    TwitchGenerationLimitPermission,
)


class PermissionTestCase(TestCase):
    def request_from(self, user):
        request = APIRequestFactory().get("/")
        request.user = user
        return request


class IsOwnerPermissionTests(PermissionTestCase):
    def setUp(self):
        self.owner = baker.make_recipe("usermanagement.user")
        self.stranger = baker.make_recipe("usermanagement.user")
        self.video = baker.make_recipe("videomanagement.video", created_by=self.owner)
        self.permission = IsOwnerPermission()

    def check(self, user, obj):
        return self.permission.has_object_permission(self.request_from(user), None, obj)

    def test_lets_the_owner_through(self):
        self.assertTrue(self.check(self.owner, self.video))

    def test_keeps_a_stranger_out(self):
        self.assertFalse(self.check(self.stranger, self.video))

    def test_lets_a_superuser_through(self):
        superuser = baker.make_recipe("usermanagement.superuser")

        self.assertTrue(self.check(superuser, self.video))

    def test_keeps_an_anonymous_visitor_out(self):
        self.assertFalse(self.check(AnonymousUser(), self.video))

    def test_resolves_a_scene_back_to_the_video_that_owns_it(self):
        scene = baker.make_recipe("videomanagement.scene", prompt=self.video.prompt)

        self.assertTrue(self.check(self.owner, scene))
        self.assertFalse(self.check(self.stranger, scene))

    def test_resolves_a_scene_image_back_to_the_video_that_owns_it(self):
        scene = baker.make_recipe("videomanagement.scene", prompt=self.video.prompt)
        scene_image = baker.make_recipe("videomanagement.scene_image", scene=scene)

        self.assertTrue(self.check(self.owner, scene_image))
        self.assertFalse(self.check(self.stranger, scene_image))


class GenerationLimitPermissionTests(PermissionTestCase):
    def check(self, permission, user):
        return permission.has_permission(self.request_from(user), None)

    def test_lets_a_user_with_balance_generate(self):
        user = baker.make_recipe("usermanagement.user", generation_limit_for_ai=5)

        self.assertTrue(self.check(AiGenerationLimitPermission(), user))

    def test_stops_a_user_who_cannot_afford_it(self):
        user = baker.make_recipe("usermanagement.user", generation_limit_for_ai=0.5)

        self.assertFalse(self.check(AiGenerationLimitPermission(), user))

    def test_lets_a_superuser_generate_whatever_their_balance(self):
        user = baker.make_recipe("usermanagement.superuser", generation_limit_for_ai=0)

        self.assertTrue(self.check(AiGenerationLimitPermission(), user))

    def test_keeps_an_anonymous_visitor_out(self):
        self.assertFalse(self.check(AiGenerationLimitPermission(), AnonymousUser()))

    def test_each_action_costs_what_it_is_worth(self):
        # A whole video costs more to start than a single scene or image.
        user = baker.make_recipe("usermanagement.user", generation_limit_for_ai=0.3)

        self.assertTrue(self.check(SceneGenerationLimitPermission(), user))
        self.assertFalse(self.check(SceneImageGenerationLimitPermission(), user))
        self.assertFalse(self.check(AiGenerationLimitPermission(), user))

    def test_twitch_is_charged_against_its_own_balance(self):
        user = baker.make_recipe(
            "usermanagement.user",
            generation_limit_for_ai=100,
            generation_limit_for_twitch=0,
        )

        self.assertFalse(self.check(TwitchGenerationLimitPermission(), user))
