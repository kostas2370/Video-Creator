"""Read narration, visual descriptions, and editing data from a saved storyboard."""

from dataclasses import dataclass
from typing import Iterator


def scene_text(sentence: dict) -> str:
    """The text that identifies a scene.

    Normally the narration. With narration switched off the script is not asked for a
    spoken line at all, so the shot description stands in — Scene rows are looked up by
    this text later, so it has to come from somewhere.
    """
    return (sentence.get("sentence") or sentence["image_description"]).strip()


@dataclass(frozen=True)
class ScriptLine:
    text: str
    image_description: str
    is_last: bool
    editing: dict = None
    shot_plan: dict = None
    narration: str = ""


def script_lines(gpt_answer: dict) -> Iterator[ScriptLine]:
    for scene in gpt_answer["scenes"]:
        sentences = scene["sentences"]
        for index, sentence in enumerate(sentences):
            yield ScriptLine(
                text=scene_text(sentence),
                image_description=sentence["image_description"],
                is_last=index == len(sentences) - 1,
                editing=sentence.get("editing"),
                shot_plan=sentence.get("shot_plan"),
                narration=(sentence.get("sentence") or "").strip(),
            )
