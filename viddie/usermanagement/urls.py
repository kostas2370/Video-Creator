
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import *


urlpatterns = [
    path('login/', LoginView.as_view(), name = "login"),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/register/', UserRegisterView.as_view(), name = "register"),
    path('api/email-verify/', VerifyEmail.as_view(), name = "email-verify"),
]
