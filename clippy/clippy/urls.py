from django.contrib import admin
from django.urls import path, include
from clippy.usermanagement.views import *
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.jwt')), path('api/token/', LoginView.as_view(), name = "login"),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/register/', UserRegisterView.as_view(), name = "register"),
    path('api/email-verify/', VerifyEmail.as_view(), name = "email-verify"),
    path('api/', include("usersapp.urls")),
    path('api/', include("posts.urls")), path('api/', include("universityapp.urls"))
]
