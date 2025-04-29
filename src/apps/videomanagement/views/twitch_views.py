from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..serializers import VideoSerializer
from ..services.TwitchGenerationService import generate_twitch_video
from ..swagger_serializers import TwitchSerializer
from ..permissions import TwitchGenerationLimitPermission
from ..throttling import TwitchGenerateRateThrottle


@swagger_auto_schema(
    operation_description="generates a video from twitch clips, depending on the game or streamer",
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
    video = generate_twitch_video(**serializer.validated_data)
    return Response(
        {
            "message": "The video has been generated successfully",
            "video": VideoSerializer(video).data,
        }
    )
