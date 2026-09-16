# The one script format used for every generation, so the shape the rest of the
# pipeline reads is always the same: scenes -> sentences -> sentence/image_description.
# prompt_utils.determine_fields resolves that shape, and audio_utils/visual_utils walk
# it to build the audio and imagery for each sentence.
default_format = """
Organise the scenario into scenes. Each scene is made up of sentences. For every
sentence, write the narration and a description of an image that illustrates it.

Answer with JSON only — no prose, no markdown, no code fences — in exactly this shape:
{
  "title": "<short title for the video>",
  "target_audience": "<who the video is for>",
  "topic": "<the topic in one line>",
  "scenes": [
    {
      "scene": "<short label for the scene>",
      "sentences": [
        {
          "sentence": "<the narration to be spoken>",
          "image_description": "<the image to show while it is spoken>"
        }
      ]
    }
  ]
}
"""
