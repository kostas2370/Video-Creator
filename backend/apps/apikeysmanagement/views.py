from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import ApiKeys
from .serializers import ApiKeysSerializer


class ApiKeysView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ApiKeysSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        keys, _ = ApiKeys.objects.get_or_create(user=self.request.user)
        return keys

    def perform_destroy(self, instance):
        instance.delete()
