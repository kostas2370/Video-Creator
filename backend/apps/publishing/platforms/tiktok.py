"""Tiktok upload and processing status."""

from urllib.parse import quote

from ..models import Platform, PublishJob
from ..providers import ProviderError, api, checked_upload_url
from .common import update, put_binary


def chunk_plan(size):
    chunk = min(size, 10 * 1024**2)
    return chunk, max(1, size // chunk)



def upload(job, token):
    options = job.options
    chunk, count = chunk_plan(job.media.size)
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



def check_status(job, token):
    result = api("POST", "https://open.tiktokapis.com/v2/post/publish/status/fetch/", token,
                 json={"publish_id": job.remote_id})["data"]
    if result["status"] == "FAILED":
        update(job, status=PublishJob.Status.FAILED, error="TikTok rejected this upload. Check the account and video requirements.")
    elif result["status"] == "PUBLISH_COMPLETE":
        ids = result.get("publicaly_available_post_id") or []
        update(job, status=PublishJob.Status.PUBLISHED, url="https://www.tiktok.com/@_/video/" + quote(str(ids[0])) if ids else "")

