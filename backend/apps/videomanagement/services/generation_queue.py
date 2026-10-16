"""Prepare a video and hand generation off to a worker."""

from rest_framework.exceptions import APIException

from ..models import VideoStatus
from .VideoGenerationServices import create_pending_video


class GenerationQueueUnavailable(APIException):
    status_code = 503
    default_detail = "Could not queue generation. Please try again."
    default_code = "generation_queue_unavailable"


def queue_video_generation(*, created_by, reference_image=None, **params):
    # Tasks import serializers and generation services; resolve this only once
    # the application has loaded, rather than introducing an import cycle.
    from ..tasks import generate_video_task

    video = create_pending_video(
        message=params["message"],
        created_by=created_by,
        video_type="AI",
        genre=params.get("genre"),
    )
    if params.get("review_script"):
        video.settings = {"generation_params": {**params, "review_script": False}}
        video.save(update_fields=["settings"])

    try:
        if reference_image:
            video.reference_image = reference_image
            video.save(update_fields=["reference_image"])
        generate_video_task.delay(video_id=video.id, **params)
    except Exception as exc:
        video.reference_image.delete(save=False)
        video.reference_image = ""
        video.status = VideoStatus.FAILED
        video.save(update_fields=["reference_image", "status"])
        raise GenerationQueueUnavailable() from exc

    return video
