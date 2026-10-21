"""YouTube resumable uploads and processing status."""

from urllib.parse import quote

import requests
from rest_framework.exceptions import ValidationError

from ..models import Platform, PublishJob
from ..http import ProviderError, request_json, checked_upload_url
from .base import Publisher
from .common import put_binary, update

API_URL = "https://www.googleapis.com/youtube/v3"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubePublisher(Publisher):
    def validate_options(self, options, metadata, size, context):
        super().validate_options(options, metadata, size, context)
        if not options["title"]:
            raise ValidationError({"title": "Add a video title."})
        if options["privacy"] not in context["privacy_level_options"]:
            raise ValidationError({"privacy": "Choose the video's visibility."})
        if "made_for_kids" not in options:
            raise ValidationError({"made_for_kids": "Choose whether this video is made for kids."})

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
        result = request_json(
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
