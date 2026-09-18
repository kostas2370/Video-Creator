from urllib.parse import quote

from django.conf import settings
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created

from .tasks import send_email


@receiver(reset_password_token_created)
def password_reset_token_created(
    sender, instance, reset_password_token, *args, **kwargs
):
    reset_url = (
        f"{settings.FRONTEND_URL}{settings.PASSWORD_RESET_PATH}"
        f"?token={quote(reset_password_token.key)}"
    )

    send_email.delay(
        name="Password Reset for Your Account",
        email=reset_password_token.user.email,
        text=f"Use the link below to reset your password:\n{reset_url}",
    )
