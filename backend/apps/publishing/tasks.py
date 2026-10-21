"""Uploads are never automatically repeated after an uncertain remote response."""

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Platform, PublishJob
from .diagnostics import log_failure
from .http import ProviderError
from .accounts import access_token
from .platforms import get_publisher
from .platforms.common import update
from .services import posting_context


@shared_task(soft_time_limit=3500, time_limit=3600, acks_late=False)
def upload_job(job_id):
    if not PublishJob.objects.filter(pk=job_id, status=PublishJob.Status.QUEUED).update(status=PublishJob.Status.UPLOADING, updated_at=timezone.now()):
        return
    job = PublishJob.objects.select_related("account", "user").get(pk=job_id)
    if not job.account or not job.user.is_active:
        update(job, status=PublishJob.Status.FAILED, error="The account was disconnected or is inactive. Nothing was sent.")
        return
    try:
        token = access_token(job.account)
        publisher = get_publisher(job.account, token)
        if job.platform == Platform.TIKTOK:
            publisher.validate_options(job.options, job.metadata, job.media.size, posting_context(job.account))
    except Exception as exc:
        log_failure("prepare_upload", platform=job.platform, reference=job.pk, error=exc)
        update(job, status=PublishJob.Status.FAILED, error="The account connection or posting permissions changed. Reconnect the account and review its settings. Nothing was uploaded.")
        return

    try:
        publisher.upload(job)
    except Exception as exc:
        log_failure("upload", platform=job.platform, reference=job.pk, error=exc)
        # A remote side effect may have succeeded before the response was lost.
        update(job, status=PublishJob.Status.NEEDS_CHECK, error="Upload confirmation was interrupted. Check the connected platform before creating another publishing request.")
        return
    schedule_status(job)


def schedule_status(job):
    try:
        poll_job.apply_async(args=[str(job.pk)], countdown=15)
    except Exception as exc:
        log_failure("queue_status", platform=job.platform, reference=job.pk, error=exc)
        update(job, status=PublishJob.Status.NEEDS_CHECK, error="The platform is processing this upload. Refresh its status here before attempting another upload.")


def poll_once(job):
    if not job.account:
        raise ProviderError("The account was disconnected. Check the result on the platform.")
    get_publisher(job.account, access_token(job.account)).check_status(job)


@shared_task(soft_time_limit=110, time_limit=120)
def poll_job(job_id):
    job = PublishJob.objects.select_related("account", "user").get(pk=job_id)
    if job.status != PublishJob.Status.PROCESSING:
        return
    if not job.user.is_active:
        update(job, status=PublishJob.Status.NEEDS_CHECK, error="The creator account is inactive. Check the platform for the upload result.")
        return
    try:
        poll_once(job)
    except Exception as exc:
        log_failure("check_status", platform=job.platform, reference=job.pk, error=exc)
        update(job, status=PublishJob.Status.NEEDS_CHECK, error="The platform status could not be confirmed. Check the platform before uploading again.")
        return
    if job.status != PublishJob.Status.PROCESSING:
        return
    if job.created_at < timezone.now() - timedelta(hours=6):
        update(job, status=PublishJob.Status.NEEDS_CHECK, error="Processing is taking longer than expected. Check the platform before uploading again.")
        return
    schedule_status(job)
