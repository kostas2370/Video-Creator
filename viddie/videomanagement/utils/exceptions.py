class InvalidJsonFormatError(Exception):

    def __init__(self):
        self.message = "Invalid Json Format"


class FileNotDownloadedError(Exception):

    def __init__(self):
        self.message = "could not download the video"
