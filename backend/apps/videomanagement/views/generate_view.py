from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import GenericAPIView
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from ..serializers.requests import GenerateSerializer
from ..serializers.models import VideoSerializer
from ..services.generation_queue import queue_video_generation
from ..throttling import GenerateRateThrottle


class GenerateView(GenericAPIView):
    serializer_class = GenerateSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [GenerateRateThrottle]

    @swagger_auto_schema(responses={202: "Video generation queued", 503: "Generation queue unavailable"})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = queue_video_generation(**serializer.validated_data)

        return Response(
            {
                "message": "The video generation has been queued",
                "video": VideoSerializer(video).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )
