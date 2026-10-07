"""An ASGI SSE endpoint, compatible with Django 4.0's synchronous HTTP views."""
import asyncio
import json
import logging
import re
import time

from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import HttpRequest
from django.http.cookie import parse_cookie
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


async def wait_for_disconnect(receive):
    while True:
        if (await receive())["type"] == "http.disconnect":
            return


class VideoEventApplication:
    def __init__(self, django_application):
        self.django_application = django_application

    async def __call__(self, scope, receive, send):
        match = EVENT_PATH.fullmatch(scope.get("path", ""))
        if scope["type"] != "http" or match is None:
            return await self.django_application(scope, receive, send)

        headers = {key.decode("latin1").lower(): value.decode("latin1")
                   for key, value in scope.get("headers", [])}
        request = HttpRequest()
        request.method = scope["method"]
        request.META = {"HTTP_" + key.upper().replace("-", "_"): value
                        for key, value in headers.items()}
        request.COOKIES = parse_cookie(headers.get("cookie", ""))
        cors = []
        try:
            host = request.get_host()
        except DisallowedHost:
            return await self.respond(send, 400)
        origin = headers.get("origin")
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

        layer = get_channel_layer("video_events")
        channel = None
        tasks = []
        started = False
        disconnected = False
        try:
            channel = await layer.new_channel()
            await asyncio.wait_for(layer.group_add(group, channel), timeout=2)
            await send({"type": "http.response.start", "status": 200, "headers": cors + [
                (b"content-type", b"text/event-stream"),
                (b"cache-control", b"no-cache, no-transform"),
                (b"x-accel-buffering", b"no"),
            ]})
            started = True
            await send({"type": "http.response.body", "body": b"event: ready\ndata: {}\n\n", "more_body": True})
            disconnect = asyncio.create_task(wait_for_disconnect(receive))
            update = asyncio.create_task(layer.receive(channel))
            tasks = [disconnect, update]
            while time.time() < expires:
                done, _ = await asyncio.wait(tasks, timeout=min(15, expires - time.time()),
                                             return_when=asyncio.FIRST_COMPLETED)
                if disconnect in done:
                    disconnected = True
                    break
                if update in done:
                    event = update.result()
                    body = ("event: update\ndata: " + json.dumps(event) + "\n\n").encode()
                    update = asyncio.create_task(layer.receive(channel))
                    tasks = [disconnect, update]
                else:
                    body = b": keepalive\n\n"
                await send({"type": "http.response.body", "body": body, "more_body": True})
        except Exception:
            logger.warning("Video event stream unavailable", exc_info=True)
            if not started:
                await self.respond(send, 503, cors)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if channel:
                try:
                    await asyncio.wait_for(layer.group_discard(group, channel), timeout=2)
                except Exception:
                    logger.warning("Could not release video event subscription", exc_info=True)
        if started and not disconnected:
            await send({"type": "http.response.body", "body": b"", "more_body": False})

    @staticmethod
    async def respond(send, status, headers=None):
        await send({"type": "http.response.start", "status": status, "headers": headers or []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
