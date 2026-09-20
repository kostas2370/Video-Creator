from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from ..swagger_serializers import GenerateSerializer
from ..services.VideoGenerationServices import create_pending_video
from ..serializers import VideoSerializer
from ..permissions import AiGenerationLimitPermission
from ..tasks import generate_video_task
from ..throttling import GenerateRateThrottle


class GenerateView(APIView):
    permission_classes = [IsAuthenticated, AiGenerationLimitPermission]
    throttle_classes = [GenerateRateThrottle]

    @swagger_auto_schema(...)
    def post(self, request):
        serializer = GenerateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        params = dict(serializer.validated_data)
        created_by = params.pop("created_by")

        video = create_pending_video(
            message=params["message"],
            created_by=created_by,
            video_type="AI",
            genre=params.get("genre"),
        )
        generate_video_task.delay(video_id=video.id, **params)

        return Response(
            {
                "message": "The video generation has been queued",
                "video": VideoSerializer(video).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )
