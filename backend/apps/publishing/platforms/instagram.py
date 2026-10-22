"""Instagram Reel containers, processing and publishing."""

from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ..models import PublishJob
from ..http import ProviderError, request_json
from ..connections.meta import meta_base
from .base import Publisher
from .common import update, validate_caption


def media_url(job):
    token = signing.dumps({"job": str(job.pk)}, salt="publishing-media")
    return f"{settings.SOCIAL_PUBLIC_BASE_URL}/api/publishing/media/{job.pk}/?" + urlencode({"token": token})


class InstagramPublisher(Publisher):
    def validate_options(self, options, metadata, size, context):
        super().validate_options(options, metadata, size, context)
        validate_caption(options["caption"])
        if (
            not 3 <= metadata["duration"] <= 900
            or size > 1024**3
            or metadata["width"] > 1920
            or not 23 <= metadata["fps"] <= 60
        ):
            raise ValidationError("Instagram Reels need a 3-second to 15-minute export, at most 1 GB and 1920 pixels wide, at 23–60 fps.")

    def upload(self, job):
        payload = {
            "media_type": "REELS",
            "video_url": media_url(job),
            "caption": job.options["caption"],
            "share_to_feed": str(job.options["share_to_feed"]).lower(),
        }
        result = request_json(
            "POST", f"{meta_base()}/{self.account.external_id}/media",
            token=self.token, data=payload,
        )
        update(job, remote_id=result["id"], status=PublishJob.Status.PROCESSING)

    def check_status(self, job):
        result = request_json(
            "GET", f"{meta_base()}/{job.remote_id}", token=self.token,
            params={"fields": "status_code"},
        )
        if result["status_code"] in ("ERROR", "EXPIRED"):
            update(job, status=PublishJob.Status.FAILED,
                   error="Instagram could not prepare this Reel. Check the video format and account permissions.")
            return
        if result["status_code"] != "FINISHED":
            return

        # Claim this irreversible step once; never automatically repeat media_publish.
        claimed = PublishJob.objects.filter(
            pk=job.pk, status=PublishJob.Status.PROCESSING,
        ).update(status=PublishJob.Status.PUBLISHING, updated_at=timezone.now())
        if not claimed:
            return
        job.status = PublishJob.Status.PUBLISHING
        published = request_json(
            "POST", f"{meta_base()}/{self.account.external_id}/media_publish",
            token=self.token, data={"creation_id": job.remote_id},
        )
        update(job, remote_id=published["id"], status=PublishJob.Status.PUBLISHED)
        try:
            permalink = request_json(
                "GET", f"{meta_base()}/{job.remote_id}", token=self.token,
                params={"fields": "permalink"},
            )
            update(job, url=permalink.get("permalink", ""))
        except ProviderError:
            pass
