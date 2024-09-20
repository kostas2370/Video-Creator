import jwt
import logging

from django.middleware import csrf
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.core.mail import send_mail

from rest_framework_simplejwt import views as jwt_views
from rest_framework import generics
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ParseError
from rest_framework_simplejwt import tokens
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.exceptions import TokenError

from .models import Login
from .serializers import RegisterSerializer, UserSerializer, LoginSerializer, VerifySerializer, CookieTokenRefreshSerializer
from .tasks import send_email

logger = logging.getLogger(__name__)


class UserRegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request):
        if get_user_model().objects.all().count() > settings.USER_LIMIT:
            return Response({"message": "User limit reached, contact the admin !"})

        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save()

        user = get_user_model().objects.get(email=serializer.data["email"])
        user.set_password(request.data["password"])
        user.save()

        token = tokens.RefreshToken.for_user(user).access_token

        current_site = get_current_site(request).domain

        absurl = f'{current_site}{reverse("email-verify")}?token={str(token)}'

        send_mail(subject ="Register verification for video creator !", recipient_list = [user.email],
                  message=f"Thank you, here is the verification link : {absurl}", from_email= settings.EMAIL_HOST_USER)

        return Response(UserSerializer(user).data, status = status.HTTP_201_CREATED)


class VerifyEmail(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = VerifySerializer

    def get(self, request):
        token = request.GET.get('token')
        try:
            load = jwt.decode(token, settings.SECRET_KEY, algorithms = 'HS256')

        except jwt.ExpiredSignatureError:
            return Response({"error": "Token Expired"}, status = 400)

        except jwt.DecodeError:
            return Response({"error": "Invalid Token"}, status = 400)

        user = get_user_model().objects.get(id = load['user_id'])
        if user.is_verified:
            return Response({"error": "User is already verified"}, status = status.HTTP_400_BAD_REQUEST)

        user.is_verified = True
        user.save()
        return Response({"email": "Successfully Activated"}, status=status.HTTP_200_OK)


class LoginView(generics.GenericAPIView):

    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.serializer_class(data = request.data, context = {'request': request})

        user = get_user_model().objects.get(username = request.data.get("username"))

        serializer.is_valid(raise_exception = True)
        user_ip = Login.get_user_ip(request)

        login, created = Login.objects.get_or_create(user = user, ip = user_ip)
        login.count += 1

        if created:
            send_email.delay(f"Someone accessed your account!", user.email, f"Someone with this ip : {user_ip} "   
                                                                            f"accessed your account,")
            user.save()

        response = Response(serializer.data, status = status.HTTP_200_OK)
        response.set_cookie("access_token", serializer.data["tokens"]["access"],
                            expires = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
                            httponly = settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
                            secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                            samesite = settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'])

        response.set_cookie("refresh_token",
                            serializer.data["tokens"]["refresh"],
                            expires = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
                            samesite = settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
                            httponly = settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
                            secure = settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"])

        response["X-CSRFToken"] = csrf.get_token(request)

        return response


class CookieTokenRefreshView(jwt_views.TokenRefreshView):
    serializer_class = CookieTokenRefreshSerializer

    def finalize_response(self, request, response, *args, **kwargs):
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

        if 'access' in response.data:
            response.set_cookie(key = "access_token",
                                value = response.data['access'],
                                expires = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
                                secure = settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                                httponly = settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'], )

        response["X-CSRFToken"] = request.COOKIES.get("csrftoken", "")
        return super().finalize_response(request, response, *args, **kwargs)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.COOKIES.get("refresh_token")
        token = tokens.RefreshToken(refresh_token)
        token.blacklist()
        res = Response()
        res.delete_cookie("access_token", samesite = "Strict", )
        res.delete_cookie("refresh_token", samesite = "Strict",)
        res.delete_cookie("X-CSRFToken", samesite = "None")
        res.delete_cookie("csrftoken", samesite = "None")
        return res

    except Exception as exc:
        logger.error(exc)
        raise ParseError("Invalid token")


