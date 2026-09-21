from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import video


class ApiTestCase(TestCase):
    def setUp(self):
        self.user = user.make()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        # Superusers skip throttling, which is what these tests care about — the rate
        # limits are covered on their own.
        throttle = patch(
            "apps.videomanagement.throttling.BaseThrottle.allow_request",
            return_value=True,
        )
        throttle.start()
        self.addCleanup(throttle.stop)

    def video_for(self, owner=None, **kwargs):
        return video.make(created_by=owner or self.user, **kwargs)
