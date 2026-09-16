from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..serializers import VideoSerializer
from ..services.VideoGenerationServices import create_pending_video
from ..services.TwitchGenerationService import twitch_video_title
from ..swagger_serializers import TwitchSerializer
from ..permissions import TwitchGenerationLimitPermission
from ..tasks import generate_twitch_video_task
from ..throttling import TwitchGenerateRateThrottle


@swagger_auto_schema(
    operation_description="Queues a video built from twitch clips, depending on the game or streamer. "
    "Returns 202 with the video in GENERATION status; poll GET /video/{id}/ "
    "until its status becomes READY or FAILED.",
    method="POST",
    request_body=TwitchSerializer,
)
@api_view(["POST"])
@permission_classes((IsAuthenticated, TwitchGenerationLimitPermission))
@throttle_classes([TwitchGenerateRateThrottle])
def generate_twitch(request):
    data = request.data.copy()
    serializer = TwitchSerializer(data=data, context=dict(request=request))
    serializer.is_valid(raise_exception=True)

    params = dict(serializer.validated_data)
    created_by = params.pop("created_by")

    # Celery's json serializer cannot carry a date; Twitch wants an ISO day anyway.
    started_at = params.get("started_at")
    params["started_at"] = started_at.isoformat() if started_at else ""

    video = create_pending_video(
        message=f"Mode : {params['mode']} Value : {params['value']}",
        created_by=created_by,
        video_type="TWITCH",
        title=twitch_video_title(params["value"]),
    )
    generate_twitch_video_task.delay(video_id=video.id, **params)

    return Response(
        {
            "message": "The video generation has been queued",
            "video": VideoSerializer(video).data,
        },
        status=status.HTTP_202_ACCEPTED,
    )
