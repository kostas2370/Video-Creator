# Shared character and setting continuity

For a new AI project, the script model drafts a shared character and setting
description as part of the storyboard request. There is no separate AI request.
The model establishes recurring subjects and their identifying details before
drafting individual shots. It may return an empty brief when no shared subject
or setting is useful; web-image projects do not request an AI continuity brief.

Review, edit, or clear the draft in **Review your storyboard** before proceeding.
Your reviewed description is saved with the project and passed to visual generation.
Clearing it during review stays cleared when the worker creates the media.

To supply your own description, open **Generation settings → Character & setting
continuity** before generation. Your description takes priority over the AI draft.
For an existing AI project (or manual project with AI visuals), open **Video settings**
to edit the stored description. Existing projects do not receive a retroactive AI draft.

Describe the recurring subjects, distinctive features, clothing, important props,
locations, and visual style. Example:

> Milo is a small orange fox with a white muzzle, green scarf, and brown satchel.
> The forest is painted in watercolor with warm evening light.

The project stores this brief and includes it in storyboard generation, new scene
drafts, and each AI visual request, including replacement visuals and custom
providers. The individual shot prompt remains editable and is stored separately;
repeated regeneration does not duplicate the brief. Characters are only included
when the shot calls for them; explicit changes in a shot can override shared details.

Saving a brief does not regenerate existing media or spend generation credits.
Regenerate the desired scenes to apply it. Clearing the field removes the guidance
from future requests. Web-image searches do not use this guidance. This is
prompt-level consistency, not a guarantee of identical characters or continuous motion.

## Extracting details from a reference image

Upload an optional reference and choose **Character**, **Style**, or **Both**.
The chosen script model receives the normalized image in the storyboard request:
OpenAI uses image content parts, Claude uses image blocks, and Gemini uses an image
blob. It must be a model that accepts images. Unsupported models fail with guidance
to select an image-capable model; the image is never silently ignored.

- **Character:** visible appearance, distinguishing features, proportions, clothing,
  and important props. The story still controls the setting and visual style.
- **Style:** medium, rendering, texture, palette, and lighting. Pictured subjects
  and locations are not adopted as characters or settings.
- **Both:** the subject details and visual style.

The model merges observations with the story and your continuity preferences.
Explicit user instructions take priority over visible reference details; reference
details take priority over invented details for the chosen role. The resulting
description and reference preview appear in storyboard review. Editing or clearing
the description takes effect on approval, and approval does not analyze the image again.

OpenAI image generation receives role-specific guidance with the reference.
Video providers use a character/both reference as the first frame. In style-only
mode, video generation uses the extracted written style instead of copying the
uploaded reference as the first frame. Later video shots can still use closing
frames from generated clips for continuity.

There is no separate analysis request; image input increases the normal storyboard
request's input usage. Existing text-only requests keep their original format.
Normalized image bytes stay out of queued task parameters and are prepared once
per storyboard request, then reused if response validation requires a retry.
Reference-role settings are stored with the project; no migration is needed.

## Sora continuation

Sora-native extension has not been implemented. OpenAI's current API reference
states that Sora 2 and the Videos API shut down on September 24, 2026:
https://developers.openai.com/api/reference/resources/videos

The historical generation guide still describes extensions. A working continuation
feature requires a supported provider with a verified continuation API. It must
also reconcile the prior clip's visible endpoint with narration trimming and
exclude any repeated source footage from the resulting scene.

No database migration is required for the shared brief. Restart the API and worker
and rebuild the frontend to use updated code in Docker.
