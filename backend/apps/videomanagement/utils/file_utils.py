import os

from django.core.exceptions import SuspiciousFileOperation


def generate_directory(name: str, x: int = 0) -> str:
    """
    Generate a directory with the given name and a numerical suffix if necessary.

    Parameters:
    -----------
    name : str
        The base name of the directory.
    x : int, optional
        The numerical suffix to be appended to the directory name. Default is 0.

    Returns:
    --------
    str
        The name of the generated directory.

    Notes:
    ------
    - This function creates a directory with the given name.
    - If a directory with the same name already exists, it appends a numerical suffix until a
      unique directory name is found.
    """

    while True:
        dir_name = (name + (" " + str(x) if x != 0 else "")).strip()
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
            os.mkdir(f"{dir_name}/dialogues")
            os.mkdir(f"{dir_name}/images")

            return dir_name
        else:
            x += 1


def check_if_image(path: str) -> bool:
    supported_image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    file_extension = os.path.splitext(path)[1].lower()
    return file_extension in supported_image_extensions


def check_if_video(path: str) -> bool:
    supported_video_extensions = {".mp4", ".avi", ".mov", ".webm", ".m4v"}
    file_extension = os.path.splitext(path)[1].lower()
    return file_extension in supported_video_extensions


def stored_file_exists(field) -> bool:
    """Whether a FileField actually has bytes behind it.

    A field can be set and the file still be gone: the ElevenLabs and 60dB calls
    swallow their own errors, and a half-finished generation leaves rows pointing at
    files that were never written. `path` also refuses anything outside MEDIA_ROOT,
    which counts as not there rather than as a crash.
    """
    if not field:
        return False

    try:
        return os.path.exists(field.path)
    except (ValueError, SuspiciousFileOperation):
        return False
