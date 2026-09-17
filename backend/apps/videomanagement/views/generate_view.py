from rest_framework.response import Response
from rest_framework import status, viewsets
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from ..models import TemplatePrompt
from ..swagger_serializers import GenerateSerializer
from ..services.VideoGenerationServices import create_pending_video
from ..serializers import VideoSerializer
from ..permissions import AiGenerationLimitPermission
from ..tasks import generate_video_task
from ..throttling import GenerateRateThrottle


class GenerateView(viewsets.GenericViewSet):
    serializer_class = GenerateSerializer
    queryset = TemplatePrompt.objects.all()
    permission_classes = [IsAuthenticated, AiGenerationLimitPermission]
    throttle_classes = [GenerateRateThrottle]

    @swagger_auto_schema(
        request_body=GenerateSerializer,
        operation_description="Queues generation of the scenes, the prompt and the scene images. "
        "Returns 202 with the video in GENERATION status; poll GET /video/{id}/ "
        "until its status becomes READY or FAILED.",
    )
    def create(self, request):
        data = request.data.copy()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        params = dict(serializer.validated_data)
        created_by = params.pop("created_by")

        video = create_pending_video(
            message=params["message"], created_by=created_by, video_type="AI"
        )
        generate_video_task.delay(video_id=video.id, **params)

        return Response(
            {
                "message": "The video generation has been queued",
                "video": VideoSerializer(video).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )
