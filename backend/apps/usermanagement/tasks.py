from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def send_email(name, email, text):
    send_mail(
        subject=name,
        message=text,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
    )
