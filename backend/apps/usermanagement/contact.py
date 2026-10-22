import logging

from django.conf import settings
from django.core.mail import EmailMessage
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class ContactThrottle(AnonRateThrottle):
    rate = "5/hour"


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=254)
    message = serializers.CharField(min_length=10, max_length=5000)
    website = serializers.CharField(required=False, allow_blank=True, max_length=200)


class ContactView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ContactThrottle]

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("website"):
            return Response({"detail": "Message received."})
        try:
            sent = EmailMessage(
                subject="Viddie contact form",
                body=f"Name: {data['name']}\nEmail: {data['email']}\n\n{data['message']}",
                from_email=settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL,
                to=[settings.CONTACT_EMAIL],
                reply_to=[data["email"]],
            ).send(fail_silently=False)
            if not sent:
                raise RuntimeError("Contact email was not sent")
        except Exception:
            logger.exception("Contact email delivery failed")
            return Response(
                {"detail": "We couldn't send your message. Please try again later or email us directly."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"detail": "Message received."})
