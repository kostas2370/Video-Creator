from rest_framework.response import Response
from rest_framework.decorators import api_view
from drf_yasg.utils import swagger_auto_schema
from ..serializers import VideoSerializer
from ..swagger_serializers import TwitchSerializer
from ..services.TwitchGenerationService import generate_twitch_video


@swagger_auto_schema(operation_description = "generates a video from twitch clips, depending on the game or streamer",
                     method = "POST",
                     request_body = TwitchSerializer)
@api_view(['POST'])
def generate_twitch(request):
    serializer = TwitchSerializer(data = request.data)
    serializer.is_valid(raise_exception = True)
    video = generate_twitch_video(**serializer.data)
    return Response(VideoSerializer(video).data)
