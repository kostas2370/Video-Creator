from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..filters import UsageFilter
from ..models import AIUsage
from ..serializers.usage import UsageSerializer
from ..services.usage import summarize_usage


class UsageView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UsageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = UsageFilter

    def get_queryset(self):
        return AIUsage.objects.filter(user=self.request.user)

    @swagger_auto_schema(responses={200: UsageSerializer})
    def get(self, request):
        all_usage = self.get_queryset()
        usage = self.filter_queryset(all_usage)
        summary = summarize_usage(
            all_usage, usage, period=request.query_params.get("period", "30")
        )
        return Response(self.get_serializer(summary).data)
