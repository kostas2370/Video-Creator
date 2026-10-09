import asyncio
from contextlib import asynccontextmanager
from unittest.mock import Mock, patch

from asgiref.sync import sync_to_async
from asgiref.testing import ApplicationCommunicator
from django.contrib.auth import get_user_model
from django.core.asgi import get_asgi_application
from django.db import transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django_eventstream.views import ListenerManager
from redis.exceptions import ConnectionError
from rest_framework_simplejwt.tokens import AccessToken

from apps.usermanagement.models import Notification

from ..events import publish_update
from ..models import Scene, SceneImage, UserPrompt, Video, VideoStatus


class EventPublicationTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="owner", email="owner@example.com"
        )
        self.other = get_user_model().objects.create_user(
            username="other", email="other@example.com"
        )
        self.video = Video.objects.create(
            created_by=self.owner,
            title="Video",
            prompt=UserPrompt.objects.create(prompt="Story"),
        )

    def test_committed_scene_visual_and_notification_writes_publish_updates(self):
        with patch("apps.videomanagement.events.send_event") as send:
            with self.captureOnCommitCallbacks(execute=True):
                scene = Scene.objects.create(video=self.video, text="A sentence")
                SceneImage.objects.create(scene=scene)
                Notification.objects.create(user=self.owner, title="Ready")
            self.assertEqual(
                [call.args[0] for call in send.call_args_list],
                [
                    f"video.{self.video.pk}",
                    f"video.{self.video.pk}",
                    f"notifications.{self.owner.pk}",
                ],
            )
            self.assertTrue(
                all(call.args[1] == "update" for call in send.call_args_list)
            )
            self.assertEqual(send.call_args_list[0].args[2]["scene_id"], str(scene.pk))

    def test_rollback_does_not_publish(self):
        with patch("apps.videomanagement.events.send_event") as send:
            with self.captureOnCommitCallbacks(execute=True):
                try:
                    with transaction.atomic():
                        publish_update(f"video.{self.video.pk}", video_id=self.video.pk)
                        raise ValueError("rollback")
                except ValueError:
                    pass
        send.assert_not_called()

    def test_delivery_failure_does_not_fail_the_write(self):
        with patch(
            "apps.videomanagement.events.send_event",
            side_effect=ConnectionError("offline"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                Scene.objects.create(video=self.video, text="Still saved")
        self.assertTrue(Scene.objects.filter(text="Still saved").exists())


@override_settings(
    ALLOWED_HOSTS=["testserver"], CORS_ALLOWED_ORIGINS=["https://frontend.example"]
)
class EventStreamTests(TransactionTestCase):
    def setUp(self):
        self.manager = ListenerManager()
        self.manager.redis_listener = None
        self.enterContext(
            patch("django_eventstream.views.listener_manager", self.manager)
        )
        self.enterContext(patch("django_eventstream.eventstream.redis_client", None))
        self.enterContext(patch("apps.videomanagement.event_stream.Redis.from_url"))
        self.owner = get_user_model().objects.create_user(
            username="owner", email="owner@example.com"
        )
        self.other = get_user_model().objects.create_user(
            username="other", email="other@example.com"
        )
        self.video = Video.objects.create(
            created_by=self.owner,
            title="Video",
            prompt=UserPrompt.objects.create(prompt="Story"),
        )
        self.application = get_asgi_application()

    @asynccontextmanager
    async def connect(
        self, user=None, path=None, method="GET", origin=None, token=None, query=b""
    ):
        headers = [(b"host", b"testserver"), (b"accept", b"text/event-stream")]
        if user:
            headers.append(
                (
                    b"cookie",
                    f"access_token={token or AccessToken.for_user(user)}".encode(),
                )
            )
        if origin:
            headers.append((b"origin", origin.encode()))
        scope = {
            "type": "http",
            "method": method,
            "scheme": "http",
            "http_version": "1.1",
            "path": path or f"/api/videos/{self.video.pk}/events/",
            "query_string": query,
            "server": ("testserver", 80),
            "headers": headers,
        }
        communicator = ApplicationCommunicator(self.application, scope)
        await communicator.send_input({"type": "http.request", "body": b""})
        try:
            yield communicator, await communicator.receive_output(timeout=3)
        finally:
            await communicator.send_input({"type": "http.disconnect"})
            await communicator.wait(timeout=3)

    async def test_cookie_authentication_and_ownership_apply_to_streams(self):
        for user, expected in ((self.owner, 200), (self.other, 404), (None, 401)):
            async with self.connect(user) as (stream, response):
                self.assertEqual(response["status"], expected)
                await stream.receive_output()
        token = AccessToken.for_user(self.owner)
        token["exp"] = 1
        async with self.connect(self.owner, token=str(token)) as (_, response):
            self.assertEqual(response["status"], 401)

    async def test_scene_and_rendering_updates_use_the_library_stream(self):
        async with self.connect(self.owner, origin="https://frontend.example") as (
            stream,
            response,
        ):
            self.assertEqual(response["status"], 200)
            headers = {key.lower(): value for key, value in response["headers"]}
            self.assertEqual(headers[b"x-accel-buffering"], b"no")
            self.assertIn(
                (b"access-control-allow-origin", b"https://frontend.example"),
                response["headers"],
            )
            self.assertIn(
                b"event: stream-open", (await stream.receive_output())["body"]
            )
            await sync_to_async(Scene.objects.create)(
                video=self.video, text="New scene"
            )
            self.assertIn(b'"kind": "scene"', (await stream.receive_output())["body"])
            self.video.status = VideoStatus.RENDERING
            await sync_to_async(self.video.save)()
            self.assertIn(b'"kind": "video"', (await stream.receive_output())["body"])
        await asyncio.sleep(0)
        self.assertFalse(self.manager.listeners_by_channel)

    async def test_video_channel_is_selected_by_the_endpoint(self):
        other_video = await sync_to_async(Video.objects.create)(
            created_by=self.other, title="Other video", prompt=self.video.prompt
        )
        async with self.connect(
            self.owner, query=f"channel=video.{other_video.pk}".encode()
        ) as (stream, response):
            self.assertEqual(response["status"], 200)
            await stream.receive_output()
            self.assertEqual(
                set(self.manager.listeners_by_channel), {f"video.{self.video.pk}"}
            )
            await sync_to_async(Scene.objects.create)(video=other_video, text="Private")
            self.assertTrue(await stream.receive_nothing(interval=0.05))
            await sync_to_async(Scene.objects.create)(
                video=self.video, text="Your scene"
            )
            self.assertIn(b'"kind": "scene"', (await stream.receive_output())["body"])

    async def test_notifications_cannot_subscribe_to_another_users_channel(self):
        async with self.connect(
            self.owner,
            path="/api/notifications/events/",
            query=f"channel=notifications.{self.other.pk}".encode(),
        ) as (stream, response):
            self.assertEqual(response["status"], 200)
            await stream.receive_output()
            self.assertEqual(
                set(self.manager.listeners_by_channel),
                {f"notifications.{self.owner.pk}"},
            )
            await sync_to_async(Notification.objects.create)(
                user=self.other, title="Other account"
            )
            self.assertTrue(await stream.receive_nothing(interval=0.05))
            await sync_to_async(Notification.objects.create)(
                user=self.owner, title="Your video is ready"
            )
            self.assertIn(
                b'"kind": "notification"', (await stream.receive_output())["body"]
            )

    async def test_wrong_origin_and_wrong_method_are_refused(self):
        for kwargs, expected in (
            ({"origin": "https://evil.example"}, 403),
            ({"method": "POST"}, 405),
        ):
            async with self.connect(self.owner, **kwargs) as (_, response):
                self.assertEqual(response["status"], expected)

    async def test_redis_outage_returns_503_for_polling_fallback(self):
        with patch(
            "apps.videomanagement.event_stream.Redis.from_url",
            side_effect=ConnectionError("offline"),
        ):
            async with self.connect(self.owner) as (_, response):
                self.assertEqual(response["status"], 503)

    async def test_token_expiry_ends_the_stream_and_releases_its_listener(self):
        token = AccessToken.for_user(self.owner)
        with patch(
            "apps.videomanagement.event_stream.time",
            Mock(time=Mock(return_value=token["exp"] - 0.05)),
        ):
            async with self.connect(self.owner, token=str(token)) as (stream, response):
                self.assertEqual(response["status"], 200)
                while (await stream.receive_output()).get("more_body", False):
                    pass
        await asyncio.sleep(0)
        self.assertFalse(self.manager.listeners_by_channel)

    def test_wsgi_returns_503_instead_of_consuming_an_endless_async_stream(self):
        self.client.cookies["access_token"] = str(AccessToken.for_user(self.owner))
        self.assertEqual(
            self.client.get(f"/api/videos/{self.video.pk}/events/").status_code, 503
        )
