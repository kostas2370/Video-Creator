from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.usermanagement.baker_recipes import superuser, user

from ..throttling import (
    GenerateRateThrottle,
    RenderRateThrottle,
    TwitchGenerateRateThrottle,
)


class RateTests(TestCase):
    def test_each_action_is_capped_at_what_it_costs_to_run(self):
        self.assertEqual(GenerateRateThrottle.rate, "2/hour")
        self.assertEqual(TwitchGenerateRateThrottle.rate, "6/hour")
        self.assertEqual(RenderRateThrottle.rate, "1/day")


class ThrottleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.addCleanup(GenerateRateThrottle().cache.clear)

    def generate_as(self, caller):
        self.client.force_authenticate(caller)
        with patch("apps.videomanagement.tasks.generate_video_task.delay"):
            return self.client.post(reverse("generate"), {"message": "cats"})

    def test_turns_a_user_away_once_they_have_used_their_allowance(self):
        caller = user.make()

        statuses = [self.generate_as(caller).status_code for _ in range(3)]

        self.assertEqual(statuses, [202, 202, 429])

    def test_never_throttles_a_superuser(self):
        admin = superuser.make()

        statuses = [self.generate_as(admin).status_code for _ in range(3)]

        self.assertEqual(statuses, [202, 202, 202])

    def test_one_users_allowance_is_their_own(self):
        first = user.make()
        second = user.make()

        for _ in range(2):
            self.generate_as(first)

        self.assertEqual(self.generate_as(second).status_code, 202)
