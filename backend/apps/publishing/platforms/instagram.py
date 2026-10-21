"""Instagram Reel containers, processing and publishing."""

from ..models import PublishJob
from ..providers import ProviderError, api, meta_base
from ..services import media_url
from .base import Publisher
from .common import update


class InstagramPublisher(Publisher):
    def upload(self, job):
        payload = {
            "media_type": "REELS",
            "video_url": media_url(job),
            "caption": job.options["caption"],
            "share_to_feed": str(job.options["share_to_feed"]).lower(),
        }
        result = api(
            "POST", f"{meta_base()}/{self.account.external_id}/media",
            token=self.token, data=payload,
        )
        update(job, remote_id=result["id"], status=PublishJob.Status.PROCESSING)

    def check_status(self, job):
        result = api(
            "GET", f"{meta_base()}/{job.remote_id}", token=self.token,
            params={"fields": "status_code"},
        )
        if result["status_code"] in ("ERROR", "EXPIRED"):
            update(job, status=PublishJob.Status.FAILED,
                   error="Instagram could not prepare this Reel. Check the video format and account permissions.")
        elif result["status_code"] == "FINISHED":
            # Claim this irreversible step once; never automatically repeat media_publish.
            claimed = PublishJob.objects.filter(
                pk=job.pk, status=PublishJob.Status.PROCESSING,
            ).update(status=PublishJob.Status.PUBLISHING)
            if not claimed:
                return
            update(job, status=PublishJob.Status.PUBLISHING)
            published = api(
                "POST", f"{meta_base()}/{self.account.external_id}/media_publish",
                token=self.token, data={"creation_id": job.remote_id},
            )
            update(job, remote_id=published["id"], status=PublishJob.Status.PUBLISHED)
            try:
                permalink = api(
                    "GET", f"{meta_base()}/{job.remote_id}", token=self.token,
                    params={"fields": "permalink"},
                )
                update(job, url=permalink.get("permalink", ""))
            except ProviderError:
                pass
