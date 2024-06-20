from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, UserSerializer, LoginSerializer, VerifySerializer
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
        if get_user_model().objects.all().count() > settings.USER_LIMIT:
            return Response({"message": "User limit reached, contact the admin !"})

        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save()

        user = get_user_model().objects.get(email=serializer.data["email"])
        user.set_password(request.data["password"])
        user.save()

        token = RefreshToken.for_user(user).access_token

        current_site = get_current_site(request).domain

        absurl = f'{current_site}{reverse("email-verify")}?token={str(token)}'

        send_email.delay("Register verification for video creator !", user.email,
                         f"Thank you, here is the verification link : {absurl}")

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
        user = get_user_model().objects.get(username = request.data["username"])
        serializer.is_valid(raise_exception = True)
        user_ip = Login.get_user_ip(request)

        login, created = Login.objects.get_or_create(user = user, ip = user_ip)
        login.count += 1

        if created:
            send_email.delay(f"Someone accessed your account!", user.email, f"Someone with this ip : {user_ip} "   
                                                                            f"accessed your account,")
            user.save()

        return Response(serializer.data, status = status.HTTP_200_OK)
