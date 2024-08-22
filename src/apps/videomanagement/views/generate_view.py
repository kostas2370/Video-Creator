from rest_framework.response import Response
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema

from ..models import TemplatePrompts, Videos
from ..swagger_serializers import GenerateSerializer
from ..services.VideoGenerationServices import generate_video
from ..serializers import VideoSerializer

import time
class GenerateView(viewsets.ViewSet):
    serializer_class = GenerateSerializer
    queryset = TemplatePrompts.objects.all()

    @swagger_auto_schema(request_body = GenerateSerializer,
                         operation_description = "This API generates the scenes , the prompt and scene images !"
                         )
    def create(self, request):
        data = request.data.copy()
        data["created_by"] = request.user.id

        serializer = self.serializer_class(data = data)

        serializer.is_valid()

        video = generate_video(**serializer.validated_data)

        return Response({"message": "The video has been generated successfully",
                         "video": VideoSerializer(video).data
                         })
