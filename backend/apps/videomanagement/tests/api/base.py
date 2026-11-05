from unittest.mock import Mock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import video
from ...tasks import generate_scene_image_task, update_scene_task
from ..draft_jobs import DraftJobTestMixin


class ApiTestCase(DraftJobTestMixin, TestCase):
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
        self.mock_draft_jobs()
        self.scene_queue = Mock()

        def record(task, *args, **kwargs):
            self.last_job_kind = "scene"
            return self.scene_queue(task, *args, **kwargs)

        for task in (update_scene_task, generate_scene_image_task):
            queue = patch.object(
                task,
                "apply_async",
                side_effect=lambda *args, _task=task, **kwargs: record(
                    _task, *args, **kwargs
                ),
            )
            queue.start()
            self.addCleanup(queue.stop)

    def run_scene_job(self):
        if self.last_job_kind == "draft":
            return self.run_draft_handler()
        queued = self.scene_queue.call_args
        task = queued.args[0]
        return task.run(*queued.kwargs["args"])

    def video_for(self, owner=None, **kwargs):
        return video.make(created_by=owner or self.user, **kwargs)
