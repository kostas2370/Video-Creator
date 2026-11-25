from smtplib import SMTPException

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import OperationalError

from .access_requests import approve_access_request


@shared_task
def send_email(name, email, text):
    send_mail(
        subject=name,
        message=text,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
    )


@shared_task(
    autoretry_for=(SMTPException, OSError, RuntimeError, OperationalError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def send_access_invitation(request_id, reviewer_id):
    reviewer = (
        get_user_model()
        .objects.filter(pk=reviewer_id, is_active=True, is_superuser=True)
        .first()
    )
    if reviewer is None:
        return False
    return approve_access_request(request_id, reviewer)
