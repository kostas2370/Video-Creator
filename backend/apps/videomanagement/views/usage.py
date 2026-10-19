from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.videomanagement.filters import UsageFilter
from apps.videomanagement.models import AIUsage
from apps.videomanagement.serializers.usage import UsageSerializer


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
