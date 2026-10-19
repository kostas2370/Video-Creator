"""Account workflows shared by the HTTP endpoints."""

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db.models import F
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as APIValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.videomanagement.events import publish_update

from .models import Login, Notification
from .tasks import send_email


def register_user(values, verification_url):
    if get_user_model().objects.count() >= settings.USER_LIMIT:
        raise PermissionDenied({"message": "User limit reached, contact the admin !"})
    user = get_user_model().objects.create_user(**values)
    token = RefreshToken.for_user(user).access_token
    send_mail(
        subject="Register verification for video creator !",
        recipient_list=[user.email],
        message=f"Thank you, here is the verification link : {verification_url}?token={token}",
        from_email=settings.EMAIL_HOST_USER,
    )
    return user


def verify_email(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms="HS256")
    except jwt.ExpiredSignatureError as exc:
        raise APIValidationError({"error": "Token Expired"}) from exc
    except jwt.DecodeError as exc:
        raise APIValidationError({"error": "Invalid Token"}) from exc
    try:
        user = get_user_model().objects.filter(id=payload["user_id"]).first()
    except (KeyError, ValidationError, ValueError, TypeError) as exc:
        raise APIValidationError({"error": "Invalid Token"}) from exc
    if user is None:
        raise APIValidationError({"error": "Invalid Token"})
    if user.is_verified:
        raise APIValidationError({"error": "User is already verified"})
    user.is_verified = True
    user.save(update_fields=["is_verified"])
    return user


def record_login(user, ip):
    login, created = Login.objects.get_or_create(user=user, ip=ip)
    Login.objects.filter(pk=login.pk).update(count=F("count") + 1)
    if created:
        send_email.delay(
            "Someone accessed your account!",
            user.email,
            f"Someone with this ip : {ip} accessed your account,",
        )


def mark_notifications_read(user):
    marked = Notification.objects.filter(user=user, read=False).update(read=True)
    if marked:
        publish_update(f"notifications.{user.pk}", kind="notification")
    return marked
