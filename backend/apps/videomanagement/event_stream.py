"""An ASGI SSE endpoint, compatible with Django 4.0's synchronous HTTP views."""
import asyncio
import json
import logging
import re
import time
from io import BytesIO

from channels.db import database_sync_to_async
from channels.consumer import AsyncConsumer
from channels.exceptions import StopConsumer
from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.core.handlers.asgi import ASGIRequest
from rest_framework.exceptions import APIException

from apps.usermanagement.authenticate import CustomAuthentication

from .models import Video

logger = logging.getLogger(__name__)
EVENT_PATH = re.compile(r"/api/(?:videos/(?P<video_id>\d+)|notifications)/events/")


@database_sync_to_async
def authorize_stream(request, video_id):
    authentication = CustomAuthentication().authenticate(request)
    if authentication is None:
        return 401, None, None
    user, token = authentication
    if video_id is not None and not Video.objects.filter(pk=video_id, created_by=user).exists():
        return 404, None, None
    group = f"video.{video_id}" if video_id is not None else f"notifications.{user.pk}"
    return 200, min(time.time() + 300, token["exp"]), group


class VideoEventConsumer(AsyncConsumer):
    channel_layer_alias = "video_events"

    def __init__(self, group, expires, headers):
        self.group = group
        self.expires = expires
        self.headers = headers
        self.started = False
        self.heartbeat = None

    async def __call__(self, scope, receive, send):
        try:
            await asyncio.wait_for(
                super().__call__(scope, receive, send),
                timeout=max(0, self.expires - time.time()),
            )
        except Exception as exc:
            if not isinstance(exc, asyncio.TimeoutError):
                logger.warning("Video event stream unavailable", exc_info=True)
            if self.started:
                await send({"type": "http.response.body", "body": b"", "more_body": False})
            else:
                await VideoEventApplication.respond(send, 503, self.headers)
        finally:
            if self.heartbeat:
                self.heartbeat.cancel()
                await asyncio.gather(self.heartbeat, return_exceptions=True)
            if hasattr(self, "channel_name"):
                try:
                    await asyncio.wait_for(self.channel_layer.group_discard(self.group, self.channel_name), timeout=2)
                except Exception:
                    logger.warning("Could not release video event subscription", exc_info=True)

    async def http_request(self, message):
        if self.started:
            return
        await asyncio.wait_for(self.channel_layer.group_add(self.group, self.channel_name), timeout=2)
        await self.send({"type": "http.response.start", "status": 200, "headers": self.headers + [
            (b"content-type", b"text/event-stream"),
            (b"cache-control", b"no-cache, no-transform"),
            (b"x-accel-buffering", b"no"),
        ]})
        self.started = True
        await self.send({"type": "http.response.body", "body": b"event: ready\ndata: {}\n\n", "more_body": True})
        self.heartbeat = asyncio.create_task(self.keepalive())

    async def video_update(self, event):
        body = ("event: update\ndata: " + json.dumps(event) + "\n\n").encode()
        await self.send({"type": "http.response.body", "body": body, "more_body": True})

    async def http_disconnect(self, message):
        raise StopConsumer()

    async def keepalive(self):
        while True:
            await asyncio.sleep(15)
            await self.send({"type": "http.response.body", "body": b": keepalive\n\n", "more_body": True})


class VideoEventApplication:
    def __init__(self, django_application):
        self.django_application = django_application

    async def __call__(self, scope, receive, send):
        match = EVENT_PATH.fullmatch(scope.get("path", ""))
        if scope["type"] != "http" or match is None:
            return await self.django_application(scope, receive, send)

        request = ASGIRequest(scope, BytesIO())
        cors = []
        try:
            host = request.get_host()
        except DisallowedHost:
            return await self.respond(send, 400)
        origin = request.headers.get("Origin")
        if origin:
            if origin != f"{scope.get('scheme', 'http')}://{host}" and origin not in [getattr(settings, "FRONTEND_URL", ""), *getattr(settings, "CORS_ALLOWED_ORIGINS", [])]:
                return await self.respond(send, 403)
            cors = [(b"access-control-allow-origin", origin.encode("latin1")),
                    (b"access-control-allow-credentials", b"true"), (b"vary", b"Origin")]
        if scope["method"] != "GET":
            return await self.respond(send, 405, cors + [(b"allow", b"GET")])
        try:
            video_id = int(match["video_id"]) if match["video_id"] else None
            status, expires, group = await authorize_stream(request, video_id)
        except APIException:
            status, expires, group = 401, None, None
        if status != 200:
            return await self.respond(send, status, cors)

        await VideoEventConsumer(group, expires, cors)(scope, receive, send)

    @staticmethod
    async def respond(send, status, headers=None):
        await send({"type": "http.response.start", "status": status, "headers": headers or []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
