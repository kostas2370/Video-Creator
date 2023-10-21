from django.db import models
from django.contrib.auth.models import AbstractBaseUser, UnicodeUsernameValidator, UserManager
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model


class User(AbstractBaseUser):
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(max_length = 20, blank = False, unique = True, validators = [username_validator])
    first_name = models.CharField(max_length = 20, blank = False)
    last_name = models.CharField(max_length = 20, blank = False)
    email = models.EmailField(unique = True)
    is_verified = models.BooleanField(default = False)
    registration_date = models.DateField(auto_now = True)
    objects = UserManager()
    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def __str__(self):
        return self.username

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'

    def get_short_name(self):
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)


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

    def __str__(self):
        return self.user.username + " (" + self.ip + ") at " + str(self.date)



