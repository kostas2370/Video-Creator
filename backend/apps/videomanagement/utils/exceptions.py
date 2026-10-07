from rest_framework.exceptions import APIException


class InvalidJsonFormatException(Exception):
    def __init__(self):
        self.message = "Invalid Json Format"
        super().__init__(self.message)


class FileNotDownloadedException(Exception):
    def __init__(self):
        self.message = "could not download the video"
        super().__init__(self.message)


class RenderFailedException(APIException):
    status_code = 400
    default_detail = (
        "Can not render the video because it is on generation or already rendering it"
    )
    default_code = "render_failed"
