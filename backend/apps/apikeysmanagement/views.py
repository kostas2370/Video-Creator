from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import viewsets, status

from .models import ApiKeys, UserCustomTTSProvider, UserCustomVisualProvider
from .serializers import (
    ApiKeysSerializer,
    UserCustomTTSProviderSerializer,
    UserCustomVisualProviderSerializer,
)
from apps.videomanagement.tasks import update_user_voices


class ApiKeysView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ApiKeysSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        keys, _ = ApiKeys.objects.get_or_create(user=self.request.user)
        return keys


class CustomProviderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserCustomTTSProviderViewSet(CustomProviderViewSet):
    serializer_class = UserCustomTTSProviderSerializer
    queryset = UserCustomTTSProvider.objects.all()

    @action(detail=True, methods=["post"], url_path="update-voices")
    def update_voices(self, request, pk=None):
        provider = self.get_object()
        update_user_voices.delay(provider.user.id, provider.name)
        return Response(status=status.HTTP_202_ACCEPTED)


class UserCustomVisualProviderViewSet(CustomProviderViewSet):
    serializer_class = UserCustomVisualProviderSerializer
    queryset = UserCustomVisualProvider.objects.all()
