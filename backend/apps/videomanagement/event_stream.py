import asyncio
import time
from contextlib import aclosing

from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.shortcuts import get_object_or_404
from django_eventstream.channelmanager import DefaultChannelManager
from django_eventstream.renderers import SSEEventRenderer
from django_eventstream.views import events
from redis import Redis, RedisError
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from .models import Video


class VideoChannelManager(DefaultChannelManager):
    def can_read_channel(self, user, channel):
        kind, _, identifier = channel.partition(".")
        if not user or not user.is_authenticated or not identifier.isdecimal():
            return False
        if kind == "video":
            return Video.objects.filter(pk=identifier, created_by=user).exists()
        return kind == "notifications" and identifier == str(user.pk)


async def authenticated_events(stream, expires):
    async with aclosing(stream):
        try:
            async with asyncio.timeout(max(0, min(300, expires - time.time()))):
                async for chunk in stream:
                    yield chunk
        except TimeoutError:
            pass


@api_view(["GET"])
@renderer_classes([JSONRenderer, SSEEventRenderer])
def event_updates(request, video_id=None):
    origin = request.headers.get("Origin")
    allowed_origins = [
        f"{request.scheme}://{request.get_host()}",
        settings.FRONTEND_URL,
        *getattr(settings, "CORS_ALLOWED_ORIGINS", []),
    ]
    if origin and origin not in allowed_origins:
        return Response(status=403)
    if video_id is not None:
        get_object_or_404(Video, pk=video_id, created_by=request.user)
    channel = (
        f"video.{video_id}"
        if video_id is not None
        else f"notifications.{request.user.pk}"
    )
    if not isinstance(request._request, ASGIRequest):
        return Response({"detail": "Event streams require an ASGI server."}, status=503)
    try:
        with Redis.from_url(
            settings.VIDEO_EVENTS_REDIS_URL, socket_connect_timeout=1, socket_timeout=1
        ) as connection:
            connection.ping()
    except RedisError:
        return Response(
            {"detail": "Event streams are temporarily unavailable."}, status=503
        )

    response = events(request, channels=[channel])
    if response.streaming:
        response.streaming_content = authenticated_events(
            response.streaming_content, request.auth["exp"]
        )
    return response
