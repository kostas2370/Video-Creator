from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import AccessRequest


@transaction.atomic
def approve_access_request(request_id, reviewer):
    access_request = (
        AccessRequest.objects.select_for_update().filter(pk=request_id).first()
    )
    if access_request is None or access_request.status != AccessRequest.Status.PENDING:
        return False
    sent = send_mail(
        subject="Your Viddie invitation",
        message=(
            "Your request for Viddie access has been approved. "
            "Create an account using this email address at "
            f"{settings.FRONTEND_URL}/register/ and verify your email to get started. "
            "AI features use your own provider keys and may incur provider charges."
        ),
        from_email=settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL,
        recipient_list=[access_request.email],
    )
    if not sent:
        raise RuntimeError("Invitation delivery failed")
    access_request.status = AccessRequest.Status.APPROVED
    access_request.reviewed_at = timezone.now()
    access_request.reviewed_by = reviewer
    access_request.save(update_fields=["status", "reviewed_at", "reviewed_by"])
    return True
