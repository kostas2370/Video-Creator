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

## Structured series cast and story formats

Series setup uses three steps: **Idea → Cast → Finish**. Choose a story format
and a visual-style preset in Idea, then add up to six recurring character cards in
Cast. Only the selected character is expanded; extra personality, wardrobe and
relationship controls are available on demand. Production and advanced settings
live in Finish. Back and the step buttons retain unsaved work, including image
requests and AI drafts. New series start with voice-over off; existing setups keep
their saved narration and other defaults.

Each has a unique name, fixed appearance, optional default wardrobe,
personality/motivation, and starting relationships. Keep fixed physical features
in appearance and editable clothes in wardrobe. Existing free-text cast/world
notes remain available for locations, props and world rules.

Choose **Animated character story** for a visual hook, conflict, escalation and
payoff or cliffhanger, or **Serial drama** for emotional hooks, relationship
stakes, revelations and cliffhangers. **General series** keeps the open-ended
workflow. The format guides the script; signature visual style controls the look.
These choices do not change narrator or rendering settings automatically.

Character appearance and wardrobe join the shared visual guidance. Personality
and relationships guide storyboard drafting. Visual guidance has a combined
3,000-character limit across cast appearance, wardrobe, world, style and labels;
provider-specific prompt limits still apply. Episode memory drafting is asked to
retain ongoing injuries, important props, wardrobe changes, relationship changes
and unresolved stakes where relevant. Review those memories before using them
for later episodes.

Before episode one, choose **Create characters with AI** to draft profiles from
the premise, visual style and story format. Review the proposal and choose **Use
proposed cast**; this does not generate images or change saved series setup.
For an individual character, optionally enter a short **Character idea** and choose
**Write description with AI**. It drafts appearance, wardrobe, personality and
relationships using the current character and series as context. **Use description**
applies only that character's text; it preserves the character ID and image. Visual
changes require reviewing the existing look again. Keeping or discarding the draft
does not modify saved profiles or generate an image.
Each card can **Generate character image with AI** using the configured OpenAI
image model, or accept an uploaded PNG, JPEG or WebP up to 10 MB and 25 million
pixels. Image generation runs in the general worker and shows progress and safe
failure messages. Uploads do not make a paid generation request.
Saving series setup also retains pending image requests, so reopening setup can
resume checking their progress and review completed images without paying again.

Review each candidate and choose **Use this look**. Existing images remain until
their replacements are accepted. Changing name, appearance, wardrobe or the shared
visual style requires reviewing the look again with **Approve current look** or
accepting a replacement. Personality and relationship edits do not invalidate the
visual approval. Save the series setup to persist these choices. Animated stories
and serial dramas require a cast; any series using character cards requires an
approved image for every character before a new episode can be drafted. General
series without a cast retain the existing workflow.

Each episode copies a labeled sheet containing its character images and, when
present, the optional shared style/world reference. The sheet is passed to
storyboard drafting and OpenAI still-image generation. For a video provider, each
shot first generates a scene-specific starting image through OpenAI, using the
episode's cast sheet, shot prompt and shared guidance. Generation stops there for
review. In the editor, approve the image, then explicitly start animation. The video
provider animates that starting image; it does not animate the cast sheet itself.
Preparing or regenerating a starting image uses an image-generation request;
animation is a separate paid request. Uploading and approving images make no AI requests. The sheet stays
the identity source for every shot instead of accumulating drift through closing
frames. A provider without reference-image support cannot be saved with character
references.

Every episode snapshots its cast and story format and keeps its copied sheet;
future series edits cannot change those inputs. Draft retries retain the original
inputs. These references improve identity guidance but do not guarantee identical
faces or frame-to-frame continuity. Explicit per-shot cast selection and
per-character voices are still planned.

Characters use a single `Character` model linked directly to their series. It
stores name, appearance, wardrobe, personality, relationships, visual style,
position, image, approval flag and image-generation status. A pending-image field
holds a proposed replacement until it is accepted. No separate profile or image
reference model is needed. Characters being prepared in the wizard can have an
empty series link until the setup is saved. Episode snapshots remain JSON.

Deploy with series migrations through `0006_single_character`, restart the API
and workers, and rebuild the frontend. The migration retains saved characters,
their order, images and approvals without generating new images. The image task
uses a request ID to avoid accepting an obsolete background result.

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
Standalone video projects use a character/both reference as the first frame. In style-only
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


### Saved starting images and image assets

AI images are archived immediately in the owner's media library, before downstream video generation. Character images, uploaded series/video references, covers, thumbnails, and scene logos also receive independent library copies. Identical image bytes reuse an asset within the same account. Removing or changing the original reference does not remove the library copy.

Character video shots save a starting-image asset and stop before animation. The
editor shows **Starting image** with its approval state. Review the characters and
composition, edit the description and regenerate, or upload a PNG, JPEG or WebP
replacement up to 10 MB. Choose **Approve starting image**, then **Animate approved
image**. New images and changes to shot guidance, cast reference, style or frame
format require preparing and approving an image again. Approval is checked again
in the worker before any animation request.

Failed animation shows a saved message and **Retry animation**, reusing the approved
image without regenerating it. Existing clips stay until a replacement succeeds.
Resume prepares missing images and never starts animation. An asset used as a scene's
starting image is protected from deletion. Restart the API and general worker and
rebuild the frontend together when upgrading; no new database migration is required.

After upgrading, run `python manage.py archive_reference_images` to archive existing character/project images and logos. Image files left in project image folders by earlier failed jobs are also added to the library. They cannot be reliably associated with a specific scene retroactively; choose them from the library when needed.
