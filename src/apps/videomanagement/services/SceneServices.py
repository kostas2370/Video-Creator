

from ..utils.prompt_utils import format_update_form
from ..utils.gpt_utils import get_update_sentence
from ..utils.audio_utils import update_scene as update
from ..models import Scene, SceneImage


def generate_scene(text: str,
                   scene: Scene) -> str:

    if text == scene.text.strip():
        return text

    if text:
        scene.text = get_update_sentence(format_update_form(scene.text, text))

    update(scene)
    return scene.text


def update_scene(text: str, scene: Scene):
    new_text = text
    scene.text = new_text if new_text else scene.text
    update(scene)
    return scene.text
