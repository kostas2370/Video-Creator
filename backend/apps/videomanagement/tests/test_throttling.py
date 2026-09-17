from unittest.mock import patch

from django.test import TestCase
from model_bakery import baker
from rest_framework.test import APIClient

from ..throttling import (
    GenerateRateThrottle,
    RenderRateThrottle,
    TwitchGenerateRateThrottle,
)


class RateTests(TestCase):
    def test_each_action_is_capped_at_what_it_costs_to_run(self):
        # A full render is the most expensive thing a worker does, so it is the rarest.
        self.assertEqual(GenerateRateThrottle.rate, "2/hour")
        self.assertEqual(TwitchGenerateRateThrottle.rate, "6/hour")
        self.assertEqual(RenderRateThrottle.rate, "1/day")


class ThrottleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.addCleanup(GenerateRateThrottle().cache.clear)

    def generate_as(self, user):
        self.client.force_authenticate(user)
        with patch("apps.videomanagement.tasks.generate_video_task.delay"):
            return self.client.post("/api/generate/", {"message": "cats"})

    def test_turns_a_user_away_once_they_have_used_their_allowance(self):
        user = baker.make_recipe("usermanagement.user")

        statuses = [self.generate_as(user).status_code for _ in range(3)]

        self.assertEqual(statuses, [202, 202, 429])

    def test_never_throttles_a_superuser(self):
        superuser = baker.make_recipe("usermanagement.superuser")

        statuses = [self.generate_as(superuser).status_code for _ in range(3)]

        self.assertEqual(statuses, [202, 202, 202])

    def test_one_users_allowance_is_their_own(self):
        first = baker.make_recipe("usermanagement.user")
        second = baker.make_recipe("usermanagement.user")

        for _ in range(2):
            self.generate_as(first)

        self.assertEqual(self.generate_as(second).status_code, 202)
