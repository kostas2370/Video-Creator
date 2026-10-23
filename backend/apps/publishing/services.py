"""Take an immutable export snapshot only after an explicit creator submission."""

from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from PIL import Image, ImageOps

from apps.videomanagement.models import Video, VideoStatus
from apps.videomanagement.utils.file_utils import stored_file_exists
from apps.videomanagement.utils.timing import video_metadata

from .config import require_configured
from .diagnostics import log_failure
from .models import Platform, PublishJob, SocialAccount
from .accounts import access_token
from .connections.tiktok import creator_info
from .platforms import get_publisher


def account_for(user, account_id):
    return get_object_or_404(SocialAccount, pk=account_id, user=user)


def posting_context(account):
    require_configured(account.platform)
    if account.platform == Platform.TIKTOK:
        info = creator_info(access_token(account))
        return {key: info.get(key) for key in (
            "creator_nickname", "privacy_level_options", "comment_disabled", "duet_disabled",
            "stitch_disabled", "max_video_post_duration_sec",
        )}
    access_token(account)
    return {"privacy_level_options": ["private", "unlisted", "public"] if account.platform == Platform.YOUTUBE else []}


def thumbnail_snapshot(video):
    """Prefer the creator's cover, falling back to the existing library thumbnail."""
    source = next((image for image in (video.cover, video.thumbnail) if stored_file_exists(image)), None)
    if source is None:
        return None
    try:
        with source.open("rb") as file, Image.open(file) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((1280, 720))
            output = BytesIO()
            image.save(output, format="JPEG", quality=90)
            return ContentFile(output.getvalue())
    except (OSError, ValueError) as exc:
        raise ValidationError("The saved thumbnail could not be read. Recreate it before publishing to YouTube.") from exc


def create_job(user, data):
    from .tasks import upload_job
    account = account_for(user, data["account"])
    require_configured(account.platform)
    # Repeated browser submissions share a key, even if the first HTTP response was lost.
    existing = PublishJob.objects.filter(user=user, request_id=data["request_id"]).first()
    if existing:
        if existing.account_id != account.pk or existing.video_id != data["video"]:
            raise ValidationError("This publishing request was already used for another account or video.")
        return existing
    context = posting_context(account)
    options = {key: value for key, value in data.items() if key not in ("account", "video", "request_id", "export_updated_at")}
    job = None
    try:
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=user.pk)
            account = get_object_or_404(SocialAccount.objects.select_for_update(), pk=account.pk, user=user)
            video = get_object_or_404(Video.objects.select_for_update(), pk=data["video"], created_by=user)
            # Serialize concurrent submissions for this creator/export before checking the key again.
            existing = PublishJob.objects.filter(user=user, request_id=data["request_id"]).first()
            if existing:
                if existing.account_id != account.pk or existing.video_id != data["video"]:
                    raise ValidationError("This publishing request was already used for another account or video.")
                return existing
            if video.updated_at != data["export_updated_at"]:
                raise ValidationError("This project changed after you opened it. Reload the video and review its export before publishing.")
            if video.status != VideoStatus.COMPLETED or not stored_file_exists(video.output):
                raise ValidationError("Export the video and wait for it to finish before publishing.")
            if account.platform == Platform.YOUTUBE and "tags" not in options:
                options["tags"] = (video.tags or {}).get("youtube", [])
            metadata = video_metadata(video.output.path)
            size = video.output.size
            get_publisher(account).validate_options(options, metadata, size, context)
            job = PublishJob(user=user, video=video, account=account, account_name=account.display_name,
                             platform=account.platform, request_id=data["request_id"], options=options, metadata=metadata)
            with video.output.open("rb") as source:
                job.media.save(f"{job.pk}.mp4", File(source), save=False)
            if account.platform == Platform.YOUTUBE:
                thumbnail = thumbnail_snapshot(video)
                if thumbnail is not None:
                    job.thumbnail.save(f"{job.pk}.jpg", thumbnail, save=False)
            job.save()
    except Exception:
        if job is not None:
            for snapshot in (job.media, job.thumbnail):
                if snapshot:
                    snapshot.delete(save=False)
        raise
    try:
        upload_job.delay(str(job.pk))
    except Exception as exc:
        log_failure("queue_upload", platform=job.platform, reference=job.pk, error=exc)
        PublishJob.objects.filter(pk=job.pk, status=PublishJob.Status.QUEUED).update(
            status=PublishJob.Status.FAILED,
            error="The upload could not be queued. Nothing was sent. Start a new publish request when the queue is available.",
            updated_at=timezone.now(),
        )
        job.refresh_from_db()
    return job
