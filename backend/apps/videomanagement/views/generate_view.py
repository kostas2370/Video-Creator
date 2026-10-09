from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from ..request_serializers import GenerateSerializer
from ..services.VideoGenerationServices import create_pending_video
from ..serializers import VideoSerializer
from ..permissions import AiGenerationLimitPermission
from ..tasks import generate_video_task
from ..throttling import GenerateRateThrottle
from ..models import VideoStatus


class GenerateView(APIView):
    permission_classes = [IsAuthenticated, AiGenerationLimitPermission]
    throttle_classes = [GenerateRateThrottle]

    @swagger_auto_schema(...)
    def post(self, request):
        serializer = GenerateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        params = dict(serializer.validated_data)
        created_by = params.pop("created_by")
        reference_image = params.pop("reference_image", None)

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
        except Exception:
            video.reference_image.delete(save=False)
            video.reference_image = ""
            video.status = VideoStatus.FAILED
            video.save(update_fields=["reference_image", "status"])
            return Response(
                {"detail": "Could not queue generation. Please try again."}, status=503
            )

        return Response(
            {
                "message": "The video generation has been queued",
                "video": VideoSerializer(video).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )
