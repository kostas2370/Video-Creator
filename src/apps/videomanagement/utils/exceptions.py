from rest_framework.exceptions import APIException


class InvalidJsonFormatError(Exception):

    def __init__(self):
        self.message = "Invalid Json Format"


class FileNotDownloadedError(Exception):

    def __init__(self):
        self.message = "could not download the video"


class GameNotFound(APIException):
    status_code = 404
    default_detail = 'Could not find a game with that name'
    default_code = 'game_not_found'


class StreamerNotFound(APIException):
    status_code = 404
    default_detail = 'Could not find a streamer with that name'
    default_code = 'streamer_not_found'


class InvalidTwitchToken(APIException):
    status_code = 400
    default_detail = 'Twitch token is missing'
    default_code = 'token_is_missing'


class HeaderInitiationError(APIException):
    status_code = 500
    default_detail = 'Headers are missing'
    default_code = 'headers_missing'
