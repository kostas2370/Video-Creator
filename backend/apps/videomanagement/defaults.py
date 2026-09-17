# The script brief, assembled from two choices: whether the visuals are stills or
# footage, and whether anything is spoken. The JSON shape stays the same either way —
# scenes -> sentences -> image_description — so the pipeline reads one structure.
# VideoGenerationServices picks the combination.

_STILL_BRIEF = """
Organise the scenario into scenes. Each scene is made up of sentences. For every
sentence, write {parts}.
"""

_VIDEO_BRIEF = """
Organise the scenario into scenes. Each scene is made up of sentences. For every
sentence, write {parts}.

Each shot is filmed separately and lasts only a few seconds, so describe one
continuous moment: name the subject, the action it performs, the setting, and the
camera move (for example a slow push in, a pan, or a locked-off shot). Keep the
subject and setting consistent from shot to shot so the finished video looks like one
piece. Do not describe cuts, titles, text on screen, or real people by name.
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


def script_format(video: bool = False, narration: bool = True) -> str:
    """Build the script brief for this combination of visual provider and narration.

    `video` asks for footage rather than a still — a video model wastes most of its
    value on "a tray of donuts". `narration` off drops the spoken line entirely rather
    than generating words nothing will ever say; the shot description then doubles as
    the scene's text.
    """
    brief = _VIDEO_BRIEF if video else _STILL_BRIEF
    visual = "a description of a short live-action shot that illustrates it"
    if not video:
        visual = "a description of an image that illustrates it"

    parts = f"the narration and {visual}" if narration else visual.capitalize()
    if not narration:
        parts = f"only {visual} — there is no narration, so write no spoken lines"

    fields = (_NARRATION_FIELD if narration else "") + _STILL_FIELD.format(
        _SHOT if video else _IMAGE
    )

    return brief.format(parts=parts) + _SHAPE.format(fields=fields)


# Kept as names for anything that imports them directly.
default_format = script_format(video=False, narration=True)
video_format = script_format(video=True, narration=True)
