"""TikTok chunked uploads and processing status."""

from urllib.parse import quote

from rest_framework.exceptions import ValidationError

from ..models import Platform, PublishJob
from ..http import ProviderError, UploadRejected, request_json, checked_upload_url
from .base import Publisher
from .common import put_binary, update, validate_caption

API_URL = "https://open.tiktokapis.com/v2/post/publish"
INIT_ERRORS = {
    "unaudited_client_can_only_post_to_private_accounts": "TikTok requires a private TikTok account and ‘Only me’ visibility while this app awaits its publishing audit. Nothing was uploaded.",
    "privacy_level_option_mismatch": "TikTok rejected the selected visibility. Refresh the account settings and choose an available visibility. Nothing was uploaded.",
    "spam_risk_too_many_posts": "This TikTok account has reached its daily posting limit. Try again later. Nothing was uploaded.",
    "spam_risk_user_banned_from_posting": "TikTok has restricted posting for this account. Check the account in TikTok. Nothing was uploaded.",
    "reached_active_user_cap": "This TikTok app has reached its daily creator limit. Try again later. Nothing was uploaded.",
}


def chunk_plan(size):
    chunk = min(size, 10 * 1024**2)
    return chunk, max(1, size // chunk)


class TikTokPublisher(Publisher):
    def validate_options(self, options, metadata, size, context):
        super().validate_options(options, metadata, size, context)
        validate_caption(options["caption"])
        if options["privacy"] not in (context.get("privacy_level_options") or []):
            raise ValidationError({"privacy": "Choose a visibility currently available to this creator."})
        maximum = context.get("max_video_post_duration_sec")
        if not maximum or metadata["duration"] > maximum:
            raise ValidationError("This export is longer than this TikTok account can post.")
        for interaction in ("comment", "duet", "stitch"):
            if context.get(interaction + "_disabled") and options["allow_" + interaction]:
                raise ValidationError("An interaction you selected is disabled by this creator's TikTok settings.")
        if not options["music_consent"]:
            raise ValidationError("Accept TikTok's music and applicable branded-content terms before posting.")
        if options["branded_content"] and options["privacy"] == "SELF_ONLY":
            raise ValidationError("Branded content cannot be private on TikTok.")

    def upload(self, job):
        options = job.options
        size = job.media.size
        chunk, count = chunk_plan(size)
        payload = {
            "post_info": {
                "title": options["caption"],
                "privacy_level": options["privacy"],
                "disable_comment": not options["allow_comment"],
                "disable_duet": not options["allow_duet"],
                "disable_stitch": not options["allow_stitch"],
                "brand_organic_toggle": options["own_brand"],
                "brand_content_toggle": options["branded_content"],
                "is_aigc": options["synthetic"],
            },
            "source_info": {
                "source": "FILE_UPLOAD", "video_size": size,
                "chunk_size": chunk, "total_chunk_count": count,
            },
        }
        try:
            result = request_json("POST", f"{API_URL}/video/init/", token=self.token, json=payload)["data"]
        except ProviderError as exc:
            exc.stage = "upload_initialization"
            message = INIT_ERRORS.get(exc.provider_code)
            if message and exc.http_status in (200, 400, 403, 429):
                rejection = UploadRejected(message, code=exc.provider_code, status=exc.http_status)
                rejection.stage = exc.stage
                raise rejection from exc
            raise
        update(job, remote_id=result["publish_id"])
        upload_url = checked_upload_url(result["upload_url"], Platform.TIKTOK)
        with job.media.open("rb") as source:
            offset = 0
            for index in range(count):
                length = size - offset if index == count - 1 else chunk
                data = source.read(length)
                if len(data) != length:
                    raise ProviderError("The saved export could not be read completely.")
                put_binary(
                    upload_url,
                    data=data,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Length": str(length),
                        "Content-Range": f"bytes {offset}-{offset + length - 1}/{size}",
                    },
                )
                offset += length
        update(job, status=PublishJob.Status.PROCESSING)

    def check_status(self, job):
        result = request_json(
            "POST", f"{API_URL}/status/fetch/", token=self.token,
            json={"publish_id": job.remote_id},
        )["data"]
        if result["status"] == "FAILED":
            update(job, status=PublishJob.Status.FAILED,
                   error="TikTok rejected this upload. Check the account and video requirements.")
        elif result["status"] == "PUBLISH_COMPLETE":
            ids = result.get("publicaly_available_post_id") or []
            url = "https://www.tiktok.com/@_/video/" + quote(str(ids[0])) if ids else ""
            update(job, status=PublishJob.Status.PUBLISHED, url=url)
