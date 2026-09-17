from django.urls import path

from .views import (
    LoginView,
    logout_view,
    CookieTokenRefreshView,
    UserRegisterView,
    VerifyEmail,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("token/refresh/", CookieTokenRefreshView.as_view()),
    path("register/", UserRegisterView.as_view(), name="register"),
    path("email-verify/", VerifyEmail.as_view(), name="email-verify"),
]
