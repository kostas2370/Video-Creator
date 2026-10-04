import logging
from uuid import uuid4

from django.utils import timezone
from rest_framework.exceptions import APIException

from ..models import Video

logger = logging.getLogger(__name__)


class QueueUnavailable(APIException):
    status_code = 503
    default_detail = "The video task could not be queued. Please retry."


def enqueue_video_task(video, task, target_status, allowed_statuses):
    """Claim a transition and invalidate unstarted messages if publication fails."""
    previous_status = video.status
    if previous_status not in allowed_statuses:
        video.refresh_from_db()
        return False

    token = uuid4()
    claimed = Video.objects.filter(pk=video.pk, status=previous_status).update(
        status=target_status, dispatch_token=token, updated_at=timezone.now()
    )
    if not claimed:
        video.refresh_from_db()
        return False

    video.refresh_from_db()
    try:
        task.delay(video_id=video.pk, dispatch_token=str(token))
    except Exception as exc:
        logger.exception("Could not publish video task for %s", video.pk)
        restored = Video.objects.filter(
            pk=video.pk, status=target_status, dispatch_token=token
        ).update(status=previous_status, dispatch_token=None, updated_at=timezone.now())
        video.refresh_from_db()
        if restored:
            raise QueueUnavailable() from exc
        # A worker already claimed this token; preserve its progress.
    return True


def start_video_task(video_id, dispatch_token, expected_status):
    if dispatch_token is None:
        # Support jobs published before dispatch tokens were introduced.
        return True
    return bool(
        Video.objects.filter(
            pk=video_id, dispatch_token=dispatch_token, status=expected_status
        ).update(dispatch_token=None, updated_at=timezone.now())
    )
