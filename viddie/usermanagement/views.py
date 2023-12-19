from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, UserSerializer, LoginSerializer
from .tasks import send_email
from rest_framework import status
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
import jwt
from django.conf import settings
from .models import Login


class UserRegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data = request.data)

        serializer.is_valid(raise_exception = True)
        serializer.save()

        user = get_user_model().objects.get(email=serializer.data["email"])

        user.set_password(request.data["password"])
        user.save()

        token = RefreshToken.for_user(user).access_token

        current_site = get_current_site(request).domain

        absurl = f'{current_site}{reverse("email-verify")}?token={str(token)}'

        send_email.delay("Register verification", user.email, f"Thank you, here is the verification link : {absurl}")

        return Response(UserSerializer(user).data, status = status.HTTP_201_CREATED)


class VerifyEmail(generics.GenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        token = request.GET.get('token')
        try:
            load = jwt.decode(token, settings.SECRET_KEY, algorithms = 'HS256')
            user = get_user_model().objects.get(id = load['user_id'])
            if not user.is_verified:
                user.is_verified = True
                user.save()
            else:
                return Response({"error": "User is already verified"}, status = status.HTTP_400_BAD_REQUEST)

            return Response({"email": "Successfuly Activated"}, status=status.HTTP_200_OK)

        except jwt.ExpiredSignatureError:
            return Response({"error": "Token Expired"}, status = status.HTTP_400_BAD_REQUEST)

        except jwt.DecodeError:
            return Response({"error": "Invalid Token"}, status = status.HTTP_400_BAD_REQUEST)


class LoginView(generics.GenericAPIView):

    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.serializer_class(data = request.data, context = {'request': request})
        user = get_user_model().objects.get(username = request.data["username"])
        serializer.is_valid(raise_exception = True)
        user_ip = Login.get_user_ip(request)
        ips = Login.objects.filter(ip = user_ip, user = user).all()
        if ips.count() == 0:
            ip = Login.objects.create(user = user, ip = user_ip)
        else:
            ip = ips[:1].get()
            ip.login_count += 1
            ip.save()
        if ip not in user.logins.all() and ip.login_count == 1:
            send_email.delay(f"Someone logined to your account !{user.email}Someone with ip of {user_ip} "
                             f"logined to your account !")
            user.save()
        return Response(serializer.data, status = status.HTTP_200_OK)
