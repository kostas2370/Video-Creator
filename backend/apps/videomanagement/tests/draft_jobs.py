"""Test helpers for queue acceptance followed by explicit worker execution."""

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core import signing
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.videomanagement.services.draft_handlers import get_handler
from apps.videomanagement.services.draft_jobs import SALT
from apps.videomanagement.tasks import draft_ai_task


class DraftJobTestMixin:
    def mock_draft_jobs(self):
        self.draft_queue = Mock()

        def record(*args, **kwargs):
            self.last_job_kind = "draft"
            return self.draft_queue(*args, **kwargs)

        queue = patch.object(draft_ai_task, "apply_async", side_effect=record)
        queue.start()
        self.addCleanup(queue.stop)

    def run_draft_handler(self):
        user_id, name, values = self.draft_queue.call_args.kwargs["args"]
        owner = get_user_model().objects.get(pk=user_id, is_active=True)
        return get_handler(name)(owner, **values)

    def complete_draft(self, response):
        """Assert the API queues, then test the handler's result or domain exception.

        The returned response describes worker output for domain assertions; it is
        not the HTTP response from the endpoint, which must always be 202.
        """
        if response.status_code >= 400:
            return response
        self.assertEqual(response.status_code, 202, response.data)
        owner_id, task_id = signing.loads(response.data["id"], salt=SALT)
        self.assertEqual(owner_id, str(self.user.pk))
        self.assertEqual(task_id, self.draft_queue.call_args.kwargs["task_id"])
        try:
            return Response(self.run_draft_handler())
        except APIException as exc:
            return exception_handler(exc, {})
