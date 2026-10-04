from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ApiKeysView, UserCustomTTSProviderViewSet


router = DefaultRouter()
router.register(r"user-custom-tts-providers", UserCustomTTSProviderViewSet, basename="user-custom-tts-providers")
urlpatterns = router.urls
urlpatterns += [
    path("api_keys/", ApiKeysView.as_view(), name="api-keys"),
]