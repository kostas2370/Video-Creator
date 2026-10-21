"""Uploads are never automatically repeated after an uncertain remote response."""

from datetime import timedelta
from urllib.parse import quote

import requests
from celery import shared_task
from django.utils import timezone

from .models import Platform, PublishJob
from .providers import ProviderError, access_token, api, checked_upload_url, meta_base
from .services import media_url, posting_context, validate_options


def update(job, **values):
    for key, value in values.items():
        setattr(job, key, value)
    job.save(update_fields=[*values, "updated_at"])


def put_binary(url, data, headers):
    try:
        response = requests.put(url, data=data, headers=headers, timeout=(10, 300), allow_redirects=False)
    except requests.RequestException as exc:
        raise ProviderError("The transfer was interrupted. Check the platform before starting another upload.") from exc
    if response.status_code not in (200, 201, 204, 206):
        raise ProviderError("The platform did not confirm the transfer. Check its status before trying again.")
    return response


def upload_youtube(job, token):
    options = job.options
    size = job.media.size
    # Initiation yields a resumable session. Never restart it automatically after an ambiguous transfer.
    response = requests.post("https://www.googleapis.com/upload/youtube/v3/videos", params={"uploadType": "resumable", "part": "snippet,status"},
        headers={"Authorization": f"Bearer {token}", "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
        json={"snippet": {"title": options["title"], "description": options["caption"]},
              "status": {"privacyStatus": options["privacy"], "selfDeclaredMadeForKids": options["made_for_kids"], "containsSyntheticMedia": options["synthetic"]}},
        timeout=(10, 90), allow_redirects=False)
    if response.status_code not in (200, 201):
        raise ProviderError("YouTube rejected upload initialization. Check the account connection and video details.")
    upload_url = checked_upload_url(response.headers.get("Location", ""), Platform.YOUTUBE)
    # The session URL contains credentials; retain it only in process memory.
    with job.media.open("rb") as source:
        result = put_binary(upload_url, source, {"Authorization": f"Bearer {token}", "Content-Type": "video/mp4", "Content-Length": str(size)})
    video_id = result.json()["id"]
    update(job, remote_id=video_id, url="https://www.youtube.com/watch?v=" + quote(video_id), status=PublishJob.Status.PROCESSING)


def tiktok_chunk_plan(size):
    chunk = min(size, 10 * 1024**2)
    return chunk, max(1, size // chunk)


def upload_tiktok(job, token):
    options = job.options
    chunk, count = tiktok_chunk_plan(job.media.size)
    result = api("POST", "https://open.tiktokapis.com/v2/post/publish/video/init/", token, json={
        "post_info": {"title": options["caption"], "privacy_level": options["privacy"],
                      "disable_comment": not options["allow_comment"], "disable_duet": not options["allow_duet"],
                      "disable_stitch": not options["allow_stitch"], "brand_organic_toggle": options["own_brand"],
                      "brand_content_toggle": options["branded_content"], "is_aigc": options["synthetic"]},
        "source_info": {"source": "FILE_UPLOAD", "video_size": job.media.size, "chunk_size": chunk, "total_chunk_count": count},
    })["data"]
    update(job, remote_id=result["publish_id"])
    url = checked_upload_url(result["upload_url"], Platform.TIKTOK)
    with job.media.open("rb") as source:
        offset = 0
        for index in range(count):
            length = job.media.size - offset if index == count - 1 else chunk
            data = source.read(length)
            if len(data) != length:
                raise ProviderError("The saved export could not be read completely.")
            put_binary(url, data, {"Content-Type": "video/mp4", "Content-Length": str(length),
                                   "Content-Range": f"bytes {offset}-{offset + length - 1}/{job.media.size}"})
            offset += length
    update(job, status=PublishJob.Status.PROCESSING)


def upload_instagram(job, token):
    result = api("POST", meta_base() + f"/{job.account.external_id}/media", token, data={
        "media_type": "REELS", "video_url": media_url(job), "caption": job.options["caption"],
        "share_to_feed": str(job.options["share_to_feed"]).lower(),
    })
    update(job, remote_id=result["id"], status=PublishJob.Status.PROCESSING)


@shared_task(soft_time_limit=3500, time_limit=3600, acks_late=False)
def upload_job(job_id):
    if not PublishJob.objects.filter(pk=job_id, status=PublishJob.Status.QUEUED).update(status=PublishJob.Status.UPLOADING, updated_at=timezone.now()):
        return
    job = PublishJob.objects.select_related("account", "user").get(pk=job_id)
    started = False
    try:
        if not job.account or not job.user.is_active:
            update(job, status=PublishJob.Status.FAILED, error="The account was disconnected or is inactive. Nothing was sent.")
            return
        token = access_token(job.account)
        if job.platform == Platform.TIKTOK:
            validate_options(job.account, job.options, job.metadata, job.media.size, posting_context(job.account))
        started = True
        {Platform.YOUTUBE: upload_youtube, Platform.TIKTOK: upload_tiktok, Platform.INSTAGRAM: upload_instagram}[job.platform](job, token)
    except Exception:
        if not started:
            update(job, status=PublishJob.Status.FAILED, error="The account connection or posting permissions changed. Reconnect the account and review its settings. Nothing was uploaded.")
            return
        # A remote side effect may have succeeded before the response was lost.
        update(job, status=PublishJob.Status.NEEDS_CHECK, error="Upload confirmation was interrupted. Check the connected platform before creating another publishing request.")
        return
    schedule_status(job)


def schedule_status(job):
    try:
        poll_job.apply_async(args=[str(job.pk)], countdown=15)
    except Exception:
        update(job, status=PublishJob.Status.NEEDS_CHECK, error="The platform is processing this upload. Refresh its status here before attempting another upload.")


def poll_once(job):
    if not job.account:
        raise ProviderError("The account was disconnected. Check the result on the platform.")
    token = access_token(job.account)
    if job.platform == Platform.YOUTUBE:
        result = api("GET", "https://www.googleapis.com/youtube/v3/videos", token,
                     params={"part": "status,processingDetails", "id": job.remote_id})
        items = result.get("items", [])
        if not items:
            raise ProviderError("YouTube has not returned this upload. Check the channel before trying again.")
        state = items[0].get("status", {}).get("uploadStatus")
        if state in ("failed", "rejected", "deleted"):
            update(job, status=PublishJob.Status.FAILED, error="YouTube could not process this video. Check YouTube Studio for details.")
        elif state == "processed":
            update(job, status=PublishJob.Status.PUBLISHED)
    elif job.platform == Platform.TIKTOK:
        result = api("POST", "https://open.tiktokapis.com/v2/post/publish/status/fetch/", token,
                     json={"publish_id": job.remote_id})["data"]
        if result["status"] == "FAILED":
            update(job, status=PublishJob.Status.FAILED, error="TikTok rejected this upload. Check the account and video requirements.")
        elif result["status"] == "PUBLISH_COMPLETE":
            ids = result.get("publicaly_available_post_id") or []
            update(job, status=PublishJob.Status.PUBLISHED, url="https://www.tiktok.com/@_/video/" + quote(str(ids[0])) if ids else "")
    else:
        result = api("GET", meta_base() + f"/{job.remote_id}", token, params={"fields": "status_code"})
        if result["status_code"] in ("ERROR", "EXPIRED"):
            update(job, status=PublishJob.Status.FAILED, error="Instagram could not prepare this Reel. Check the video format and account permissions.")
        elif result["status_code"] == "FINISHED":
            # Claim the irreversible step once. Never automatically repeat media_publish.
            if not PublishJob.objects.filter(pk=job.pk, status=PublishJob.Status.PROCESSING).update(status=PublishJob.Status.PUBLISHING):
                return
            update(job, status=PublishJob.Status.PUBLISHING)
            published = api("POST", meta_base() + f"/{job.account.external_id}/media_publish", token, data={"creation_id": job.remote_id})
            update(job, remote_id=published["id"], status=PublishJob.Status.PUBLISHED)
            try:
                permalink = api("GET", meta_base() + f"/{job.remote_id}", token, params={"fields": "permalink"})
                update(job, url=permalink.get("permalink", ""))
            except ProviderError:
                pass


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
    except Exception:
        update(job, status=PublishJob.Status.NEEDS_CHECK, error="The platform status could not be confirmed. Check the platform before uploading again.")
        return
    if job.status == PublishJob.Status.PROCESSING:
        if job.created_at < timezone.now() - timedelta(hours=6):
            update(job, status=PublishJob.Status.NEEDS_CHECK, error="Processing is taking longer than expected. Check the platform before uploading again.")
        else:
            schedule_status(job)
