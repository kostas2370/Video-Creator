from django.urls import path

from .views import CallbackView, ConnectionsView, ConnectionView, ConnectView, ContextView, JobsView, MediaView, RefreshView

urlpatterns = [
    path("connections/", ConnectionsView.as_view(), name="publishing-connections"),
    path("connections/<uuid:account_id>/", ConnectionView.as_view(), name="publishing-disconnect"),
    path("connections/<uuid:account_id>/context/", ContextView.as_view(), name="publishing-context"),
    path("oauth/<str:platform>/start/", ConnectView.as_view(), name="publishing-connect"),
    path("oauth/<str:platform>/callback/", CallbackView.as_view(), name="publishing-callback"),
    path("jobs/", JobsView.as_view(), name="publishing-jobs"),
    path("jobs/<uuid:job_id>/refresh/", RefreshView.as_view(), name="publishing-refresh"),
    path("media/<uuid:job_id>/", MediaView.as_view(), name="publishing-media"),
]
