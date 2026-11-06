from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.filters import UserFilterSet

from .models import ApiKeys, UserCustomTTSProvider, UserCustomVisualProvider
from .serializers import (
    ApiKeysSerializer,
    UserCustomTTSProviderSerializer,
    UserCustomVisualProviderSerializer,
)
from .services import queue_voice_refresh


class ApiKeysView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ApiKeysSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        keys, _ = ApiKeys.objects.get_or_create(user=self.request.user)
        return keys


class CustomProviderViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilterSet
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserCustomTTSProviderViewSet(CustomProviderViewSet):
    serializer_class = UserCustomTTSProviderSerializer
    queryset = UserCustomTTSProvider.objects.all()

    @action(detail=True, methods=["post"], url_path="update-voices")
    def update_voices(self, request, pk=None):
        provider = self.get_object()
        queue_voice_refresh(provider)
        return Response(status=status.HTTP_202_ACCEPTED)


class UserCustomVisualProviderViewSet(CustomProviderViewSet):
    serializer_class = UserCustomVisualProviderSerializer
    queryset = UserCustomVisualProvider.objects.all()
