import logging

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.middleware import csrf
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, mixins, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    action,
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import ParseError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt import tokens
from rest_framework_simplejwt import views as jwt_views
from rest_framework_simplejwt.exceptions import TokenError

from .filters import NotificationFilter
from .models import Login, Notification
from .serializers import (
    ContactSerializer,
    CookieTokenRefreshSerializer,
    LoginSerializer,
    NotificationSerializer,
    RegisterSerializer,
    UserSerializer,
    VerifySerializer,
)
from .services import (
    mark_notifications_read,
    record_login,
    register_user,
    send_contact_message,
    verify_email,
)
from .throttling import ContactThrottle, LoginThrottle

logger = logging.getLogger(__name__)


class UserRegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification_url = (
            f"{get_current_site(request).domain}{reverse('email-verify')}"
        )
        user = register_user(serializer.validated_data, verification_url)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class VerifyEmail(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = VerifySerializer

    def get(self, request):
        verify_email(request.query_params.get("token"))
        return Response({"email": "Successfully Activated"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def csrf_token(request):
    response = Response({"detail": "CSRF token issued."})
    response["X-CSRFToken"] = csrf.get_token(request)
    response["Cache-Control"] = "no-store"
    return response


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)
    authentication_classes = []
    throttle_classes = [LoginThrottle]

    def get_authenticate_header(self, request):
        return "Bearer"

    def post(self, request):
        SessionAuthentication().enforce_csrf(request)
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        record_login(serializer.user, Login.get_user_ip(request))

        response = Response(serializer.data, status=status.HTTP_200_OK)

        remember_me = serializer.validated_data.get("remember_me", False)
        access_max_age = refresh_max_age = None
        if remember_me:
            access_max_age = int(
                settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
            )
            refresh_max_age = int(settings.REMEMBER_ME_REFRESH_LIFETIME.total_seconds())

        response.set_cookie(
            "access_token",
            serializer.data["tokens"]["access"],
            max_age=access_max_age,
            httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
            secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
            samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
        )

        response.set_cookie(
            "refresh_token",
            serializer.data["tokens"]["refresh"],
            max_age=refresh_max_age,
            samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
            secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
        )

        csrf.rotate_token(request)
        response["X-CSRFToken"] = csrf.get_token(request)

        return response


class CookieTokenRefreshView(jwt_views.TokenRefreshView):
    serializer_class = CookieTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        SessionAuthentication().enforce_csrf(request)
        return super().post(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        if response.status_code == 403:
            return super().finalize_response(request, response, *args, **kwargs)
        refresh = request.COOKIES.get("refresh_token")

        if not refresh:
            response.data = {"Message": "You need to set refresh token"}
            response.status_code = 400
            return super().finalize_response(request, response, *args, **kwargs)

        try:
            token = tokens.RefreshToken(refresh)
        except TokenError:
            response.data = {"Message": "This token has expired"}
            response.status_code = 400
            return super().finalize_response(request, response, *args, **kwargs)

        if "access" in response.data:
            remember_me = bool(token.get("remember_me", False))
            response.set_cookie(
                key="access_token",
                value=response.data["access"],
                max_age=int(
                    settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
                )
                if remember_me
                else None,
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            )

        response["X-CSRFToken"] = request.COOKIES.get("csrftoken", "")
        return super().finalize_response(request, response, *args, **kwargs)


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    SessionAuthentication().enforce_csrf(request)
    refresh_token = request.COOKIES.get("refresh_token")
    if not refresh_token:
        raise ParseError("Invalid token")

    try:
        token = tokens.RefreshToken(refresh_token)
        token.blacklist()
        res = Response()
        res.delete_cookie(
            "access_token",
            samesite="Strict",
        )
        res.delete_cookie(
            "refresh_token",
            samesite="Strict",
        )
        # CSRF is not an authentication credential. Keep it in sync with the
        # browser's cached header; the next successful login rotates it.
        return res

    except Exception as exc:
        logger.error(exc)
        raise ParseError("Invalid token")


class NotificationView(
    mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = NotificationFilter
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        notifications = self.filter_queryset(self.get_queryset())

        return Response(
            {
                "unread": self.filterset_class.unread_count(notifications),
                "results": self.get_serializer(notifications[:30], many=True).data,
            }
        )

    @action(detail=False, methods=["PATCH"])
    def read_all(self, request):
        return Response({"read": mark_notifications_read(request.user)})


class ContactView(generics.GenericAPIView):
    serializer_class = ContactSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ContactThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        send_contact_message(**serializer.validated_data)
        return Response({"detail": "Message received."})
