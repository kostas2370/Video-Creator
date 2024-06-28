
from ..models import Scene
from ..utils.audio_utils import update_scene as update
from ..utils.gpt_utils import get_update_sentence
from ..utils.prompt_utils import format_update_form


def generate_scene(text: str,
                   scene: Scene) -> str:
    """
    Generate an updated version of the scene text and update the scene with it.

    Args:
        text (str): The new text for the scene.
        scene (Scene): The scene instance to update.

    Returns:
        str: The updated text for the scene.
    """

    if text == scene.text.strip():
        return text

    if text:
        scene.text = get_update_sentence(format_update_form(scene.text, text))

    update(scene)
    return scene.text


def update_scene(text: str, scene: Scene):
    """
    Update the text of a scene with new content.

    Args:
        text (str): The new text content for the scene.
        scene (Scene): The scene object to update.

    Returns:
        str: The updated text content of the scene.
    """
    new_text = text
    scene.text = new_text if new_text else scene.text
    update(scene)
    return scene.text

