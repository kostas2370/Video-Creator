from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import PermissionsMixin


class User(AbstractUser, PermissionsMixin):

    first_name = models.CharField(max_length = 20, blank = False)
    last_name = models.CharField(max_length = 20, blank = False)
    email = models.EmailField(unique = True)
    is_verified = models.BooleanField(default = False)
    registration_date = models.DateField(auto_now = True)

    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'

    def get_short_name(self):
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def get_tokens(self):
        tokens = RefreshToken.for_user(self)

        return {"access": str(tokens.access_token),
                "refresh": str(tokens)}


class Login(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    ip = models.CharField(max_length=15)
    date = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_user_ip(cls, req):
        x_forwarded_for = req.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = req.META.get('REMOTE_ADDR')

        return ip

    @classmethod
    def get_user_login_count(cls, user):
        count = Login.objects.filter(user = user).count()
        return count

    def __str__(self):
        return self.user.username + " (" + self.ip + ") at " + str(self.date)
