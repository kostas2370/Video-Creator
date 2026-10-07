import time
from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from asgiref.testing import ApplicationCommunicator
from channels.layers import InMemoryChannelLayer
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpRequest
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from ..event_stream import VideoEventApplication, authorize_stream
from ..events import publish_update
from ..models import Scene, SceneImage, UserPrompt, Video
from apps.usermanagement.models import Notification


class EventAuthorizationTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="owner", email="owner@example.com")
        self.other = get_user_model().objects.create_user(username="other", email="other@example.com")
        self.video = Video.objects.create(created_by=self.owner, title="Video", prompt=UserPrompt.objects.create(prompt="Story"))

    def request_for(self, user):
        request = HttpRequest()
        request.COOKIES = {"access_token": str(AccessToken.for_user(user))}
        return request

    def test_only_owner_can_subscribe_to_video(self):
        status, expires, group = async_to_sync(authorize_stream)(self.request_for(self.owner), self.video.pk)
        self.assertEqual(status, 200)
        self.assertEqual(group, f"video.{self.video.pk}")
        self.assertLessEqual(expires, time.time() + 300)
        self.assertEqual(async_to_sync(authorize_stream)(self.request_for(self.other), self.video.pk)[0], 404)

    def test_notifications_are_scoped_to_authenticated_owner(self):
        status, _, group = async_to_sync(authorize_stream)(self.request_for(self.owner), None)
        self.assertEqual((status, group), (200, f"notifications.{self.owner.pk}"))

    def test_anonymous_and_expired_tokens_are_refused(self):
        self.assertEqual(async_to_sync(authorize_stream)(HttpRequest(), self.video.pk)[0], 401)
        token = AccessToken.for_user(self.owner)
        token["exp"] = int(time.time()) - 1
        request = HttpRequest()
        request.COOKIES = {"access_token": str(token)}
        self.assertEqual(async_to_sync(authorize_stream)(request, self.video.pk)[0], 401)

    def test_committed_scene_visual_and_notification_writes_publish_invalidations(self):
        layer = AsyncMock()
        with patch("apps.videomanagement.events.get_channel_layer", return_value=layer):
            with self.captureOnCommitCallbacks(execute=True):
                scene = Scene.objects.create(video=self.video, text="A sentence")
                SceneImage.objects.create(scene=scene)
                Notification.objects.create(user=self.owner, title="Ready")
            groups = [call.args[0] for call in layer.group_send.call_args_list]
            self.assertEqual(groups, [f"video.{self.video.pk}", f"video.{self.video.pk}", f"notifications.{self.owner.pk}"])

    def test_rollback_does_not_publish(self):
        layer = AsyncMock()
        with patch("apps.videomanagement.events.get_channel_layer", return_value=layer):
            with self.captureOnCommitCallbacks(execute=True):
                try:
                    with transaction.atomic():
                        publish_update(f"video.{self.video.pk}", video_id=self.video.pk)
                        raise ValueError("rollback")
                except ValueError:
                    pass
        layer.group_send.assert_not_called()

    def test_delivery_failure_does_not_fail_the_write(self):
        with patch("apps.videomanagement.events.get_channel_layer", side_effect=OSError("offline")):
            with self.captureOnCommitCallbacks(execute=True):
                Scene.objects.create(video=self.video, text="Still saved")
        self.assertTrue(Scene.objects.filter(text="Still saved").exists())


class EventCookieStreamTests(TransactionTestCase):
    # The ASGI communicator runs authorization in another thread; commit fixtures
    # instead of holding TestCase's wrapping transaction open across that thread.
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="owner", email="owner@example.com")
        self.other = get_user_model().objects.create_user(username="other", email="other@example.com")
        self.video = Video.objects.create(created_by=self.owner, title="Video", prompt=UserPrompt.objects.create(prompt="Story"))

    @override_settings(ALLOWED_HOSTS=["testserver"])
    async def test_asgi_authenticates_cookie_and_rejects_foreign_video(self):
        for user, expected in ((self.owner, 200), (self.other, 404)):
            scope = {"type": "http", "method": "GET", "scheme": "http",
                     "path": f"/api/videos/{self.video.pk}/events/",
                     "headers": [(b"host", b"testserver"),
                                 (b"cookie", f"access_token={AccessToken.for_user(user)}".encode())]}
            layer = InMemoryChannelLayer()
            with patch("apps.videomanagement.event_stream.get_channel_layer", return_value=layer):
                communicator = ApplicationCommunicator(VideoEventApplication(AsyncMock()), scope)
                await communicator.send_input({"type": "http.request", "body": b""})
                self.assertEqual((await communicator.receive_output())["status"], expected)
                await communicator.receive_output()
                await communicator.send_input({"type": "http.disconnect"})
                await communicator.wait()


@override_settings(ALLOWED_HOSTS=["testserver"], CORS_ALLOWED_ORIGINS=["https://frontend.example"])
class EventStreamTests(SimpleTestCase):
    def scope(self, path="/api/videos/7/events/", method="GET", origin=None):
        headers = [(b"host", b"testserver")]
        if origin:
            headers.append((b"origin", origin.encode()))
        return {"type": "http", "path": path, "method": method, "scheme": "http", "headers": headers}

    async def test_stream_delivers_event_and_releases_subscription_on_disconnect(self):
        layer = InMemoryChannelLayer()
        with patch("apps.videomanagement.event_stream.authorize_stream", new=AsyncMock(return_value=(200, time.time() + 300, "video.7"))), patch("apps.videomanagement.event_stream.get_channel_layer", return_value=layer):
            communicator = ApplicationCommunicator(VideoEventApplication(AsyncMock()), self.scope(origin="https://frontend.example"))
            await communicator.send_input({"type": "http.request", "body": b""})
            start = await communicator.receive_output()
            self.assertEqual(start["status"], 200)
            self.assertIn((b"x-accel-buffering", b"no"), start["headers"])
            self.assertIn((b"access-control-allow-origin", b"https://frontend.example"), start["headers"])
            self.assertIn(b"event: ready", (await communicator.receive_output())["body"])
            await layer.group_send("video.7", {"type": "video.update", "kind": "scene", "scene_id": 4})
            self.assertIn(b'"scene_id": 4', (await communicator.receive_output())["body"])
            await communicator.send_input({"type": "http.disconnect"})
            await communicator.wait()
            self.assertFalse(layer.groups.get("video.7"))

    async def test_unauthorized_wrong_origin_and_wrong_method_are_refused(self):
        for scope, expected in ((self.scope(origin="https://evil.example"), 403), (self.scope(method="POST"), 405), (self.scope(), 401)):
            with patch("apps.videomanagement.event_stream.authorize_stream", new=AsyncMock(return_value=(401, None, None))):
                communicator = ApplicationCommunicator(VideoEventApplication(AsyncMock()), scope)
                await communicator.send_input({"type": "http.request", "body": b""})
                self.assertEqual((await communicator.receive_output())["status"], expected)
                await communicator.wait()

    async def test_redis_outage_returns_503_for_polling_fallback(self):
        layer = AsyncMock()
        layer.new_channel.side_effect = OSError("offline")
        with patch("apps.videomanagement.event_stream.authorize_stream", new=AsyncMock(return_value=(200, time.time() + 300, "video.7"))), patch("apps.videomanagement.event_stream.get_channel_layer", return_value=layer):
            communicator = ApplicationCommunicator(VideoEventApplication(AsyncMock()), self.scope())
            await communicator.send_input({"type": "http.request", "body": b""})
            self.assertEqual((await communicator.receive_output())["status"], 503)
            await communicator.wait()

    async def test_expiry_ends_stream_and_other_routes_stay_with_django(self):
        layer = InMemoryChannelLayer()
        with patch("apps.videomanagement.event_stream.authorize_stream", new=AsyncMock(return_value=(200, time.time() + .01, "video.7"))), patch("apps.videomanagement.event_stream.get_channel_layer", return_value=layer):
            communicator = ApplicationCommunicator(VideoEventApplication(AsyncMock()), self.scope())
            await communicator.send_input({"type": "http.request", "body": b""})
            await communicator.receive_output()
            await communicator.receive_output()
            while True:
                message = await communicator.receive_output()
                if not message.get("more_body"):
                    break
            await communicator.wait()
            self.assertFalse(layer.groups.get("video.7"))
        django_application = AsyncMock()
        await VideoEventApplication(django_application)(self.scope(path="/api/videos/7/"), AsyncMock(), AsyncMock())
        django_application.assert_awaited_once()
