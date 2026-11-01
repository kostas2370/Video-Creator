from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.usage.estimates import media_estimate
from apps.usage.filters import UsageFilter
from apps.usage.models import AIUsage, GenerationEstimate
from apps.usage.serializers import (
    CostEstimateRequestSerializer,
    ScenarioEstimateRequestSerializer,
    UsageSerializer,
)
from apps.usage.scenarios import (
    scenario_estimate,
    project_estimate,
    include_scenario,
    missing_scenario_line,
    recorded_scenario_line,
)
from apps.videomanagement.models import Video


class UsageView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UsageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = UsageFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AIUsage.objects.none()
        return AIUsage.objects.filter(user=self.request.user)

    @swagger_auto_schema(responses={200: UsageSerializer})
    def get(self, request):
        all_usage = self.get_queryset()
        summary = self.filter_queryset(all_usage).summary()
        summary.update(
            period=request.query_params.get("period", "30"),
            first_recorded_at=all_usage.first_recorded_at(),
        )
        return Response(self.get_serializer(summary).data)


class CostEstimateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CostEstimateRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        video = get_object_or_404(
            Video.objects.select_related("voice_model", "created_by"),
            pk=data["video_id"],
            created_by=request.user,
        )
        scene = (
            get_object_or_404(video.scenes, pk=data["scene_id"])
            if "scene_id" in data
            else None
        )
        estimate = media_estimate(
            video,
            data.get("storyboard"),
            scene=scene,
            operation=data["operation"],
            text=data.get("text"),
        )
        if scene is None and data["operation"] == "all":
            estimate = project_estimate(video, data.get("storyboard"))
        return Response(estimate)


class ScenarioEstimateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ScenarioEstimateRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(scenario_estimate(serializer.validated_data, request.user))


class ProjectCostView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UsageSerializer

    def get(self, request, video_id):
        video = get_object_or_404(Video, pk=video_id, created_by=request.user)
        saved = GenerationEstimate.objects.filter(video=video).first()
        summary = AIUsage.objects.filter(
            user=request.user,
            video=video,
            service__in=("text", "images", "tts", "video"),
        ).summary()
        estimate = saved.estimate if saved else None
        if (
            estimate
            and video.video_type != "MANUAL"
            and not any(line["service"] == "text" for line in estimate["lines"])
        ):
            estimate = include_scenario(estimate, missing_scenario_line())
        return Response(
            {
                "estimate": estimate,
                "scenario": recorded_scenario_line(video),
                "recorded": UsageSerializer(
                    {**summary, "period": "all", "first_recorded_at": None}
                ).data,
            }
        )
