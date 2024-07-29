from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import *

urlpatterns = [
    path('login/', LoginView.as_view(), name = "login"),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('register/', UserRegisterView.as_view(), name = "register"),
    path('email-verify/', VerifyEmail.as_view(), name = "email-verify"),
]
