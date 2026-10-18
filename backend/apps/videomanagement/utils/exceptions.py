from rest_framework.exceptions import APIException


class VoiceProviderError(APIException):
    status_code = 502
    default_detail = "ElevenLabs could not complete the request. Please try again."


class GenerationQueueUnavailable(APIException):
    status_code = 503
    default_detail = "Could not queue generation. Please try again."
    default_code = "generation_queue_unavailable"


class VideoEditConflict(APIException):
    status_code = 409
    default_detail = "Wait for the current video operation to finish."
    default_code = "video_edit_conflict"


class InvalidJsonFormatException(Exception):
    def __init__(self):
        self.message = "Invalid Json Format"
        super().__init__(self.message)


class RenderFailedException(APIException):
    status_code = 400
    default_detail = (
        "Can not render the video because it is on generation or already rendering it"
    )
    default_code = "render_failed"
