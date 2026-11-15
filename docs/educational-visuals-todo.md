# To do: educational visuals

Goal: explain relationships, change, and cause and effect through visuals rendered
locally. GPT supplies structured instructions in the existing storyboard response;
these features must not require additional image or video generation calls.
Normal storyboard model usage still applies.

Build on the existing animated diagrams, photo motion, labels, arrows, and local
preview/export workflow. The teaching pattern is: show the whole idea, focus on
one part, explain the change, then recap.

## Features, in priority order

### 1. Step-by-step diagram reveals

- [ ] Extend existing diagrams with explicit reveal order, active-step highlights,
      and animated connections between stages.
- [ ] Let GPT plan when each step appears and how it connects to the narration.
- [ ] Make step order, timing, labels, and highlights editable before export.

### 2. Annotated images

- [ ] Add numbered markers, callout labels, circles, and spotlights to uploaded or
      existing images.
- [ ] Support focused close-ups and a return to the full image for context.
- [ ] Let users review and adjust GPT-proposed annotation positions and timing.

### 3. Animated charts and quantities

- [ ] Add locally rendered bars, line charts, percentage counters, gauges, and
      fraction illustrations.
- [ ] Reveal supplied values progressively and highlight the relevant comparison
      during the explanation.
- [ ] Keep values, units, labels, and scales editable; do not invent factual data.

### 4. Cause-and-effect animations

- [ ] Add reusable shapes, arrows, particles, and states to illustrate a sequence
      of changes, such as heat entering water and particles moving faster.
- [ ] Let GPT choose supported templates and specify the starting state, trigger,
      visible change, and explanatory labels.
- [ ] Present simplified teaching illustrations with clear labels and consistent
      preview and export behavior.

### 5. Worked examples

- [ ] Reveal calculations or solutions one step at a time.
- [ ] Highlight the terms or values that change, retaining enough previous work
      for the viewer to follow the reasoning.
- [ ] Allow editing of each step, its explanation, and its display duration.

### 6. Question, pause, and reveal

- [ ] Add question cards with an adjustable thinking pause and optional countdown.
- [ ] Reveal the answer followed by its explanation, with optional choice
      highlighting.
- [ ] Let GPT plan the question and reveal within the existing storyboard request.

## Shared foundation

- [ ] Define validated, structured visual instructions using supported templates
      and animation choices.
- [ ] Provide matching local editor previews and exported video rendering.
- [ ] Preserve manual edits when resuming generation or reopening a project.
- [ ] Support narration-related timing; make approximate timing clear wherever
      word-level alignment is unavailable.
- [ ] Keep text readable across portrait and landscape frames and allow enough
      time to understand each step.

## Later: subject-specific templates

- [ ] Add reusable templates for water cycles, circuits, number lines, fractions,
      and orbits, with editable labels and animation parameters.

Suggested first release: step-by-step diagram reveals and annotated images,
followed by charts and quantities. Add specialized templates after the shared
instruction and rendering foundation is established.
