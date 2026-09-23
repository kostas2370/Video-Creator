from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.usermanagement.baker_recipes import superuser, user

from ...baker_recipes import scene, scene_image, video
from ...permissions import (
    AiGenerationLimitPermission,
    IsOwnerPermission,
    SceneGenerationLimitPermission,
    SceneImageGenerationLimitPermission,
    TwitchGenerationLimitPermission,
)


class PermissionTestCase(TestCase):
    def request_from(self, caller):
        request = APIRequestFactory().get("/")
        request.user = caller
        return request


class IsOwnerPermissionTests(PermissionTestCase):
    def setUp(self):
        self.owner = user.make()
        self.stranger = user.make()
        self.video = video.make(created_by=self.owner)
        self.permission = IsOwnerPermission()

    def check(self, caller, obj):
        return self.permission.has_object_permission(
            self.request_from(caller), None, obj
        )

    def test_lets_the_owner_through(self):
        self.assertTrue(self.check(self.owner, self.video))

    def test_keeps_a_stranger_out(self):
        self.assertFalse(self.check(self.stranger, self.video))

    def test_lets_a_superuser_through(self):
        admin = superuser.make()

        self.assertTrue(self.check(admin, self.video))

    def test_keeps_an_anonymous_visitor_out(self):
        self.assertFalse(self.check(AnonymousUser(), self.video))

    def test_keeps_a_deactivated_owner_out(self):
        self.owner.is_active = False
        self.owner.save()

        self.assertFalse(self.check(self.owner, self.video))

    def test_keeps_a_deactivated_superuser_out(self):
        admin = superuser.make()
        admin.is_active = False
        admin.save()

        self.assertFalse(self.check(admin, self.video))

    def test_resolves_a_scene_back_to_the_video_that_owns_it(self):
        line = scene.make(video=self.video)

        self.assertTrue(self.check(self.owner, line))
        self.assertFalse(self.check(self.stranger, line))

    def test_resolves_a_scene_image_back_to_the_video_that_owns_it(self):
        line = scene.make(video=self.video)
        image = scene_image.make(scene=line)

        self.assertTrue(self.check(self.owner, image))
        self.assertFalse(self.check(self.stranger, image))


class GenerationLimitPermissionTests(PermissionTestCase):
    def check(self, permission, caller):
        return permission.has_permission(self.request_from(caller), None)

    def test_lets_a_user_with_balance_generate(self):
        caller = user.make(generation_limit_for_ai=5)

        self.assertTrue(self.check(AiGenerationLimitPermission(), caller))

    def test_stops_a_user_who_cannot_afford_it(self):
        caller = user.make(generation_limit_for_ai=0.5)

        self.assertFalse(self.check(AiGenerationLimitPermission(), caller))

    def test_lets_a_superuser_generate_whatever_their_balance(self):
        caller = superuser.make(generation_limit_for_ai=0)

        self.assertTrue(self.check(AiGenerationLimitPermission(), caller))

    def test_keeps_an_anonymous_visitor_out(self):
        self.assertFalse(self.check(AiGenerationLimitPermission(), AnonymousUser()))

    def test_each_action_costs_what_it_is_worth(self):
        # A whole video costs more to start than a single scene or image.
        caller = user.make(generation_limit_for_ai=0.3)

        self.assertTrue(self.check(SceneGenerationLimitPermission(), caller))
        self.assertFalse(self.check(SceneImageGenerationLimitPermission(), caller))
        self.assertFalse(self.check(AiGenerationLimitPermission(), caller))

    def test_twitch_is_charged_against_its_own_balance(self):
        caller = user.make(
            generation_limit_for_ai=100,
            generation_limit_for_twitch=0,
        )

        self.assertFalse(self.check(TwitchGenerationLimitPermission(), caller))
