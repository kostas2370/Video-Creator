from rest_framework.exceptions import APIException


class ContactDeliveryUnavailable(APIException):
    status_code = 503
    default_detail = (
        "We couldn't send your message. Please try again later or email us directly."
    )
    default_code = "contact_delivery_unavailable"
