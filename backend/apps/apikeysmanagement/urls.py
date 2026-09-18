from django.urls import path

from .views import ApiKeysView

urlpatterns = [
    path("api_keys/", ApiKeysView.as_view(), name="api-keys"),
]
