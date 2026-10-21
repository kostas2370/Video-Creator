VIDEO_INSTRUCTIONS = (
    "For each image_description, describe one short continuous video shot: subject, "
    "one achievable action, setting, and camera move (a slow push in, pan, or locked-off shot). "
    "Match the selected visual style; do not assume live action. "
    "Do not describe edits, cuts, titles, or text overlays."
)

_STILL_BRIEF = """
Organise the scenario into scenes. Each scene is made up of sentences. For every
sentence, write {parts}.
"""

_SHAPE = """
Answer with JSON only — no prose, no markdown, no code fences — in exactly this shape:
{{
  "title": "<short title for the video>",
  "target_audience": "<who the video is for>",
  "topic": "<the topic in one line>",
  "scenes": [
    {{
      "scene": "<short label for the scene>",
      "sentences": [
        {{{fields}
        }}
      ]
    }}
  ]
}}
"""

_NARRATION_FIELD = '\n          "sentence": "<the narration to be spoken>",'
_STILL_FIELD = '\n          "image_description": "{}"'
_SHOT = "<the shot to film: subject, action, setting, camera move>"
_IMAGE = "<the image to show while it is spoken>"


def script_format(video: bool = False, narration: bool = True, image_mode: str = None) -> str:
    brief = _STILL_BRIEF
    visual = "a description of a short video shot that illustrates it"
    if not video:
        visual = "a description of an image that illustrates it"

    if image_mode == "WEB":
        brief = _STILL_BRIEF
        visual = "one concise image search query that illustrates it"

    parts = f"the narration and {visual}" if narration else visual.capitalize()
    if not narration:
        parts = f"only {visual} — there is no narration, so write no spoken lines"

    fields = (_NARRATION_FIELD if narration else "") + _STILL_FIELD.format(
        "<concise image search terms>" if image_mode == "WEB" else _SHOT if video else _IMAGE
    )

    return brief.format(parts=parts) + _SHAPE.format(fields=fields)
