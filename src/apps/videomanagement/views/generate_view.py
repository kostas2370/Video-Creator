from rest_framework.response import Response
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from ..models import TemplatePrompts
from ..swagger_serializers import GenerateSerializer
from ..services.VideoGenerationServices import generate_video
from ..serializers import VideoSerializer
from ..permissions import AiGenerationLimitPermission
from ..throttling import GenerateRateThrottle


class GenerateView(viewsets.GenericViewSet):
    serializer_class = GenerateSerializer
    queryset = TemplatePrompts.objects.all()
    permission_classes = [IsAuthenticated, AiGenerationLimitPermission]
    throttle_classes = [GenerateRateThrottle]

    @swagger_auto_schema(request_body = GenerateSerializer,
                         operation_description = "This API generates the scenes , the prompt and scene images !"
                         )
    def create(self, request):
        data = request.data.copy()
        serializer = self.get_serializer(data = data)
        serializer.is_valid()

        video = generate_video(**serializer.validated_data)

        return Response({"message": "The video has been generated successfully",
                         "video": VideoSerializer(video).data
                         })


