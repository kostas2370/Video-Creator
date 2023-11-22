from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()


@shared_task
def send_email(name, email, text):
    send_mail(subject = name, message = text, from_email = settings.EMAIL_HOST_USER, recipient_list = [email])
