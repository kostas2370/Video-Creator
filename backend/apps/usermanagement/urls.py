from django.urls import include, path
from rest_framework import routers

from apps.videomanagement.event_stream import event_updates

from .views import (
    AccessRequestView,
    ContactView,
    CookieTokenRefreshView,
    LoginView,
    NotificationView,
    UserRegisterView,
    VerifyEmail,
    csrf_token,
    deployment,
    logout_view,
)

router = routers.DefaultRouter()
router.register("notifications", NotificationView, basename="notification")


urlpatterns = [
    path("deployment/", deployment, name="deployment"),
    path("csrf/", csrf_token, name="csrf-token"),
    path("access-requests/", AccessRequestView.as_view(), name="access-request"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("notifications/events/", event_updates, name="notification_events"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("register/", UserRegisterView.as_view(), name="register"),
    path("email-verify/", VerifyEmail.as_view(), name="email-verify"),
    path(
        "password_reset/",
        include("django_rest_passwordreset.urls", namespace="password_reset"),
    ),
]

urlpatterns += router.urls
