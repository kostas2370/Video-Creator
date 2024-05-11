import os


def generate_directory(name: str, x: int = 0) -> str:

    while True:
        dir_name = (name + (' ' + str(x) if x is not 0 else '')).strip()
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
            os.mkdir(rf'{dir_name}\dialogues')
            os.mkdir(rf'{dir_name}\images')

            return dir_name
        else:
            x += 1


def check_which_file_exists(images: list) -> str:
    for i in images:
        if os.path.exists(i):
            return i

    return None
