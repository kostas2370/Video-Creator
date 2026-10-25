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
