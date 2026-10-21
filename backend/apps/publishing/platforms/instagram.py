"""Instagram upload and processing status."""

from ..models import PublishJob
from ..providers import ProviderError, api, meta_base
from ..services import media_url
from .common import update


def upload(job, token):
    result = api("POST", meta_base() + f"/{job.account.external_id}/media", token, data={
        "media_type": "REELS", "video_url": media_url(job), "caption": job.options["caption"],
        "share_to_feed": str(job.options["share_to_feed"]).lower(),
    })
    update(job, remote_id=result["id"], status=PublishJob.Status.PROCESSING)



def check_status(job, token):
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

