"""YouTube resumable uploads and processing status."""

from urllib.parse import quote

import requests

from ..models import Platform, PublishJob
from ..providers import ProviderError, api, checked_upload_url
from .base import Publisher
from .common import put_binary, update

API_URL = "https://www.googleapis.com/youtube/v3"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubePublisher(Publisher):
    def upload(self, job):
        options = job.options
        size = job.media.size
        metadata = {
            "snippet": {"title": options["title"], "description": options["caption"]},
            "status": {
                "privacyStatus": options["privacy"],
                "selfDeclaredMadeForKids": options["made_for_kids"],
                "containsSyntheticMedia": options["synthetic"],
            },
        }
        # Never restart a resumable session automatically after an ambiguous transfer.
        response = requests.post(
            UPLOAD_URL,
            params={"uploadType": "resumable", "part": "snippet,status"},
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(size),
            },
            json=metadata,
            timeout=(10, 90),
            allow_redirects=False,
        )
        if response.status_code not in (200, 201):
            raise ProviderError("YouTube rejected upload initialization. Check the account connection and video details.")
        upload_url = checked_upload_url(response.headers.get("Location", ""), Platform.YOUTUBE)
        # The session URL contains credentials; retain it only in process memory.
        with job.media.open("rb") as source:
            result = put_binary(
                upload_url,
                data=source,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(size),
                },
            )
        video_id = result.json()["id"]
        update(job, remote_id=video_id, url="https://www.youtube.com/watch?v=" + quote(video_id),
               status=PublishJob.Status.PROCESSING)

    def check_status(self, job):
        result = api(
            "GET", f"{API_URL}/videos", token=self.token,
            params={"part": "status,processingDetails", "id": job.remote_id},
        )
        items = result.get("items", [])
        if not items:
            raise ProviderError("YouTube has not returned this upload. Check the channel before trying again.")
        state = items[0].get("status", {}).get("uploadStatus")
        if state in ("failed", "rejected", "deleted"):
            update(job, status=PublishJob.Status.FAILED,
                   error="YouTube could not process this video. Check YouTube Studio for details.")
        elif state == "processed":
            update(job, status=PublishJob.Status.PUBLISHED)
