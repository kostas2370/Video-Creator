from contextlib import asynccontextmanager
from unittest.mock import patch

from asgiref.sync import sync_to_async
from asgiref.testing import ApplicationCommunicator
from django.core.asgi import get_asgi_application
from django.test import TransactionTestCase, override_settings
from django_eventstream.views import ListenerManager
from rest_framework_simplejwt.tokens import AccessToken

from apps.clips.models import ClipProject
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.events import publish_update


@override_settings(ALLOWED_HOSTS=["testserver"])
class ClipEventTests(TransactionTestCase):
    def setUp(self):
        self.manager = ListenerManager()
        self.manager.redis_listener = None
        self.enterContext(
            patch("django_eventstream.views.listener_manager", self.manager)
        )
        self.enterContext(patch("django_eventstream.eventstream.redis_client", None))
        self.enterContext(patch("apps.videomanagement.event_stream.Redis.from_url"))
        self.owner, self.other = user.make(), user.make()
        self.project = ClipProject.objects.create(
            created_by=self.owner, title="Interview"
        )
        self.application = get_asgi_application()

    @asynccontextmanager
    async def connect(self, owner=None, query=b"", origin=None, expired=False):
        headers = [(b"host", b"testserver"), (b"accept", b"text/event-stream")]
        if owner:
            token = AccessToken.for_user(owner)
            if expired:
                token["exp"] = 1
            headers.append((b"cookie", f"access_token={token}".encode()))
        if origin:
            headers.append((b"origin", origin.encode()))
        scope = {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "http_version": "1.1",
            "path": f"/api/clips/{self.project.pk}/events/",
            "query_string": query,
            "server": ("testserver", 80),
            "headers": headers,
        }
        stream = ApplicationCommunicator(self.application, scope)
        await stream.send_input({"type": "http.request", "body": b""})
        try:
            yield stream, await stream.receive_output(timeout=3)
        finally:
            await stream.send_input({"type": "http.disconnect"})
            await stream.wait(timeout=3)

    async def test_stream_requires_cookie_authentication_ownership_and_valid_origin(
        self,
    ):
        for owner, expected in ((self.owner, 200), (self.other, 404), (None, 401)):
            async with self.connect(owner) as (_, response):
                self.assertEqual(response["status"], expected)
        async with self.connect(self.owner, expired=True) as (_, response):
            self.assertEqual(response["status"], 401)
        async with self.connect(self.owner, origin="https://other.example") as (
            _,
            response,
        ):
            self.assertEqual(response["status"], 403)

    async def test_events_use_only_the_owned_project_channel(self):
        async with self.connect(self.owner, query=b"channel=clips.someone-else") as (
            stream,
            response,
        ):
            self.assertEqual(response["status"], 200)
            await stream.receive_output()
            self.assertEqual(
                set(self.manager.listeners_by_channel), {f"clips.{self.project.pk}"}
            )
            await sync_to_async(publish_update)("clips.someone-else", kind="clips")
            self.assertTrue(await stream.receive_nothing(interval=0.05))
            await sync_to_async(publish_update)(
                f"clips.{self.project.pk}", kind="clips"
            )
            body = (await stream.receive_output())["body"]
            self.assertIn(b'"kind": "clips"', body)
            self.assertNotIn(b"words", body)
