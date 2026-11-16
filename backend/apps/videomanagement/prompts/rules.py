"""Language and story progression shared by video prompt builders."""

import json

_LANGUAGE_INSTRUCTIONS = (
    "Use the language explicitly requested by the user; otherwise use the user's language. "
    "Keep titles, character dialogue and narration in that language. Do not translate existing narration "
    "unless requested."
)


_STORY_PROGRESSION_INSTRUCTIONS = (
    "Build a clear progression: hook → development → payoff. "
    "Open with a specific question, situation, or tension relevant to the user's topic. "
    "Each scene or story beat must add new information, advance the action, or reveal a consequence; "
    "avoid repeating earlier points in different words. "
    "Develop the opening through logically connected beats, then end with a clear answer, "
    "resolution, or takeaway that delivers on it. Avoid misleading hooks and invented factual claims. "
    "Adapt this progression to the requested genre, structure, and length; these are story beats, "
    "not a requirement for exactly three scenes. For very short outputs, combine beats naturally. "
    "Do not add hook, development, or payoff labels to the output."
)


def narration_language_instruction(language):
    if not language:
        return ""
    return (
        "\nNARRATION LANGUAGE: " + json.dumps(language, ensure_ascii=False) + ". "
        "Write all narration, spoken dialogue and the video title in this selected language. "
        "This explicit selection takes precedence over the language of the creative brief "
        "and prior episodes. Keep character names and factual meaning intact.\n"
    )
