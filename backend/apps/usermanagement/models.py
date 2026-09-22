from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import PermissionsMixin
from django.core.mail import send_mail
from django.db import models
from rest_framework_simplejwt.tokens import RefreshToken


class User(AbstractUser, PermissionsMixin):
    first_name = models.CharField(max_length=20, blank=False)
    last_name = models.CharField(max_length=20, blank=False)
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    generation_limit_for_ai = models.FloatField(default=0)
    generation_limit_for_twitch = models.FloatField(default=0)
    use_service_api_keys = models.BooleanField(default=True)

    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_short_name(self):
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def get_tokens(self, remember_me: bool = False):
        tokens = RefreshToken.for_user(self)
        access = str(tokens.access_token)

        if remember_me:
            tokens["remember_me"] = True
            tokens.set_exp(lifetime=settings.REMEMBER_ME_REFRESH_LIFETIME)

        return {"access": access, "refresh": str(tokens)}


class Login(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    ip = models.CharField(max_length=15)
    date = models.DateTimeField(auto_now_add=True)
    count = models.PositiveIntegerField(default=0)

    @staticmethod
    def get_user_ip(req):
        x_forwarded_for = req.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = req.META.get("REMOTE_ADDR")

        return ip

    def __str__(self):
        return self.user.username + " (" + self.ip + ") at " + str(self.date)


class Notification(models.Model):
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=100)
    message = models.TextField(blank=True, default="")
    link = models.CharField(max_length=255, blank=True, default="")
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "read"])]

    def __str__(self):
        return f"{self.title} for {self.user}"
