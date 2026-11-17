"""Read narration, visual descriptions, and editing data from a saved storyboard."""

from dataclasses import dataclass
from typing import Iterator


def shot_diagram(shot: dict):
    editing = shot.get("editing")
    return editing.get("diagram") if isinstance(editing, dict) else None


def scene_text(sentence: dict) -> str:
    """Use narration, or a visual's own text to identify a silent shot."""
    if sentence.get("sentence"):
        return sentence["sentence"].strip()
    diagram = shot_diagram(sentence)
    if diagram:
        return (
            diagram.get("title")
            or " → ".join(item["label"] for item in diagram["items"])
        ).strip()
    return sentence.get("image_description", "").strip()


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
                image_description=""
                if shot_diagram(sentence)
                else sentence.get("image_description", ""),
                is_last=index == len(sentences) - 1,
                editing=sentence.get("editing"),
                shot_plan=sentence.get("shot_plan"),
                narration=(sentence.get("sentence") or "").strip(),
            )
