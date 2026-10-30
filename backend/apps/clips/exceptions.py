from rest_framework.exceptions import APIException


class ClipConflict(APIException):
    status_code = 409
    default_detail = "This project changed. Reload it before continuing."


class ClipQueueUnavailable(APIException):
    status_code = 503
    default_detail = "Upload saved, but processing could not be queued. Please retry."
