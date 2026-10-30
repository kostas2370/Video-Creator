from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.http import FileResponse, HttpResponseRedirect, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.ranges import parse_byte_range
from apps.videomanagement.models import Video

from . import oauth
from .config import setup_message
from .diagnostics import log_failure
from .models import Platform, PublishJob, SocialAccount
from .http import ProviderError
from .serializers import AccountSerializer, JobSerializer, PublishSerializer
from .services import account_for, create_job, posting_context
from .tasks import poll_job
from .throttling import ConnectionThrottle, ContextThrottle, PublishingThrottle, StatusThrottle


class CreatorView(APIView):
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, ProviderError):
            log_failure("account_request", platform=self.kwargs.get("platform", "unknown"), reference=self.request.user.pk, error=exc)
            error = APIException(str(exc))
            error.status_code = 502
            exc = error
        return super().handle_exception(exc)


class ConnectionsView(CreatorView):
    def get(self, request):
        return Response({
            "platforms": [{"id": key, "name": label, "configured": not setup_message(key), "setup_message": setup_message(key)} for key, label in Platform.choices],
            "accounts": AccountSerializer(SocialAccount.objects.filter(user=request.user), many=True).data,
        })


class ConnectionView(CreatorView):
    def delete(self, request, account_id):
        account = account_for(request.user, account_id)
        PublishJob.objects.filter(account=account, status=PublishJob.Status.QUEUED).update(
            status=PublishJob.Status.FAILED, error="The account was disconnected before uploading."
        )
        account.delete()
        return Response(status=204)


class ConnectView(CreatorView):
    throttle_classes = [ConnectionThrottle]

    def post(self, request, platform):
        video_id = serializers.UUIDField(required=False, allow_null=True).run_validation(request.data.get("video"))
        video = get_object_or_404(Video, pk=video_id, created_by=request.user) if video_id else None
        url, browser = oauth.begin(request.user, platform, video)
        response = Response({"url": url})
        response.set_cookie(oauth.COOKIE_NAME, browser, max_age=600, secure=True, httponly=True,
                            samesite="Lax", path=oauth.COOKIE_PATH)
        return response


class CallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, platform):
        target = "/connections/"
        result = "failed"
        try:
            attempt = oauth.consume(platform, request.query_params.get("state", ""), request.COOKIES.get(oauth.COOKIE_NAME, ""))
            if attempt.video_id:
                target = f"/videos/{attempt.video_id}/"
            if request.query_params.get("code") and not request.query_params.get("error"):
                oauth.finish(attempt, request.query_params["code"])
                result = "connected"
            elif platform == Platform.TIKTOK and "non_sandbox_target" in (
                request.query_params.get("error"), request.query_params.get("error_type"),
            ):
                result = "tiktok_sandbox_required"
        except (ValidationError, ProviderError, KeyError, ValueError, TypeError) as exc:
            log_failure("oauth_callback", platform=platform, reference="callback", error=exc)
        response = HttpResponseRedirect(settings.FRONTEND_URL + target + "?" + urlencode({"publishing": result}))
        response.delete_cookie(oauth.COOKIE_NAME, path=oauth.COOKIE_PATH, samesite="Lax")
        response["Referrer-Policy"] = "no-referrer"
        response["Cache-Control"] = "no-store"
        return response


class ContextView(CreatorView):
    throttle_classes = [ContextThrottle]

    def get(self, request, account_id):
        account = account_for(request.user, account_id)
        return Response(posting_context(account))


class JobsView(CreatorView):
    def get_throttles(self):
        return [PublishingThrottle()] if self.request.method == "POST" else []

    def get(self, request):
        jobs = PublishJob.objects.filter(user=request.user)
        video_id = request.query_params.get("video")
        if video_id:
            video_id = serializers.UUIDField().run_validation(video_id)
            get_object_or_404(Video, pk=video_id, created_by=request.user)
            jobs = jobs.filter(video_id=video_id)
        return Response(JobSerializer(jobs[:30], many=True).data)

    def post(self, request):
        serializer = PublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(JobSerializer(create_job(request.user, serializer.validated_data)).data, status=202)


class RefreshView(CreatorView):
    throttle_classes = [StatusThrottle]

    def post(self, request, job_id):
        job = get_object_or_404(PublishJob, pk=job_id, user=request.user)
        if job.status == PublishJob.Status.NEEDS_CHECK and job.remote_id and job.platform != Platform.INSTAGRAM:
            job.status = PublishJob.Status.PROCESSING
            job.error = ""
            job.save(update_fields=["status", "error", "updated_at"])
        if job.status == PublishJob.Status.PROCESSING:
            try:
                poll_job.delay(str(job.pk))
            except Exception:
                raise ValidationError("The status check could not be queued. No additional upload was started.")
        elif job.status in (PublishJob.Status.UPLOADING, PublishJob.Status.PUBLISHING) and job.updated_at < timezone.now() - timedelta(hours=1):
            job.status = PublishJob.Status.NEEDS_CHECK
            job.error = "The upload worker did not confirm completion. Check the platform before posting again."
            job.save(update_fields=["status", "error", "updated_at"])
        return Response(JobSerializer(job).data)


class MediaView(APIView):
    """Only a time-limited, job-scoped signature exposes an export to Meta's fetcher."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, job_id):
        try:
            payload = signing.loads(request.query_params.get("token", ""), salt="publishing-media", max_age=86400)
            if payload != {"job": str(job_id)}:
                raise signing.BadSignature()
        except signing.BadSignature:
            return Response(status=404)
        job = get_object_or_404(PublishJob.objects.select_related("user"), pk=job_id, platform=Platform.INSTAGRAM)
        if not job.user.is_active or not job.media or not job.media.storage.exists(job.media.name):
            return Response(status=404)
        size = job.media.size
        try:
            requested = parse_byte_range(request.headers.get("Range"), size)
        except ValueError:
            return Response(status=416, headers={"Content-Range": f"bytes */{size}"})
        if requested is not None:
            start, end = requested
            def chunks():
                with job.media.open("rb") as source:
                    source.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        data = source.read(min(1024 * 1024, remaining))
                        if not data:
                            break
                        remaining -= len(data)
                        yield data
            response = StreamingHttpResponse(chunks(), status=206, content_type="video/mp4")
            response["Content-Length"] = str(end - start + 1)
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
        else:
            response = FileResponse(job.media.open("rb"), content_type="video/mp4")
        response["Accept-Ranges"] = "bytes"
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "no-referrer"
        response["X-Content-Type-Options"] = "nosniff"
        return response
