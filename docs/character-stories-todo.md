# To do: character-driven AI video stories

Goal: support both short animated character stories, like Bananito-style fruit
dramas, and cinematic serial dramas with relationship stakes and cliffhangers,
like ReelShort-style episodes. Both use the same cast and continuity workflow.

## Implemented foundation: series cast and story formats

- [x] Save up to six named character cards in series setup, with fixed appearance,
      default wardrobe, personality/motivation, and starting relationships.
- [x] Keep existing free-text cast/world notes and the shared cast-sheet reference.
- [x] Snapshot cast and format per episode; future profile edits do not change old
      episode snapshots or generation retries.
- [x] Pass fixed appearance and wardrobe into the existing shared visual guidance.
      Pass all character details into the storyboard request.
- [x] Offer General, Animated character story, and Serial drama formats. Animation
      emphasizes visual action and payoff; drama emphasizes relationship stakes,
      revelations and cliffhangers. Rendering style remains separately editable.
- [x] Ask episode memory drafting to track relevant props, injuries, wardrobe,
      relationships and unresolved stakes, using the existing review mechanism.
- [x] Draft character profiles with AI before episode one; review and accept the
      proposal without changing saved setup until the user saves it.
- [x] Generate or upload one reference image per series character. Review new
      images before replacing existing looks, and require renewed approval when
      identity, wardrobe or shared visual style changes.
- [x] Require approved character images before drafting a story episode. Copy a
      labeled cast sheet into each episode so later cast edits cannot affect it.
- [x] Use the episode cast sheet for still-image generation and for generating a
      separate starting image per video shot before animation. Reject unsupported
      providers and keep failed replacements from overwriting existing visuals.

Still planned: a cross-series character library, standalone-video cast panels,
multiple reference images per character, explicit per-shot cast selection,
per-character dialogue/voices, and starting-image approval before animation.
Apply series migrations through `0004_characterreference`, restart the API and
general worker, and rebuild the frontend to use it in Docker.

Suggested first-release defaults: 30–60 seconds, portrait format, 2–3 characters,
and 6–10 simple shots. These are product defaults, not model limits.

## Minimum features, in build order

### 1. Cast per video

- [ ] Add a Cast panel to video creation and editing.
- [ ] Give each character a name, appearance description, personality, and 1–3
      reference images.
- [x] Separate fixed appearance from default wardrobe and story/relationship notes
      in series character cards. Per-shot appearance changes remain a later step.
- [ ] Save characters for reuse across videos and series. Keep each video's cast
      snapshot so later library edits do not silently change existing projects.

### 2. Cast selection per shot

- [ ] Let users select which characters appear in each shot.
- [ ] Include only the selected characters' descriptions in shot generation.
- [ ] Pass their reference images through a supported generation workflow; show
      provider limitations instead of silently ignoring references.
- [ ] Keep character identity references separate from shot starting frames and
      shared visual style.

### 3. Approve images before animation

- [x] Generate a starting image for each series video shot using its cast
      references, setting, action, and shared style.
- [ ] Let users review, edit, regenerate, or upload the starting image.
- [ ] Animate the approved image with an image-to-video model.
- [ ] Use previous-shot frames where continuity helps, rather than forcing every
      shot to start from the previous clip's last frame.
- [ ] Preserve approved media when prompts change; flag affected shots as needing
      review and require an explicit generation action before paid requests.

### 4. Visual story preset

- [ ] Add a character-story preset: hook → conflict → escalation → payoff or
      cliffhanger.
- [ ] Generate editable shots with cast, location, visible action, emotion, camera
      framing, and target duration.
- [ ] Support visual storytelling without narration, alongside optional narration.
- [ ] Reuse existing music, captions, storyboard, and export controls.

### 5. Retry individual shots

- [ ] Reuse or extend existing replacement controls to regenerate one starting
      image or one animation without rebuilding the whole video.
- [ ] Retain the existing approved result until its replacement succeeds and is
      accepted.
- [ ] Make each shot's generation status and failure reason visible.

## First-release workflow

Idea → choose cast → review story → approve shot images → animate shots → add
music/captions → export.

## Later, if needed

- [ ] Speaker-labelled dialogue and a saved voice per character.
- [ ] Synchronized character speech if talking-character stories are a priority.
- [ ] Multiple saved character looks and richer location references.
- [ ] Advanced continuity controls and additional model choices.

## Completion check

- [ ] Create and export a short story with two recurring characters appearing in
      multiple locations.
- [ ] Confirm each shot uses its selected cast and approved starting image.
- [ ] Review generated results for recognizable characters; references improve
      consistency but do not guarantee it.
- [ ] Replace one unsuccessful shot without changing the other approved shots.
- [ ] Reuse the cast in another video without altering the original project.

Implementation note: extend the existing storyboard, video providers, continuity,
series, and editor workflows rather than creating a separate production system.
