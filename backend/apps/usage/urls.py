from django.urls import path

from .views import UsageView

urlpatterns = [path("usage/", UsageView.as_view(), name="ai_usage")]
