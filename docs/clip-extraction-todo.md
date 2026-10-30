# To do: better clip extraction

Goal: find more complete, interesting, and distinct moments while keeping
suggestions reviewable and provider costs visible.

## First priorities

- [ ] Build a small, manually reviewed evaluation set of representative videos:
      interviews, podcasts, talks, and reaction content. Include different
      languages, good moments, poor candidates, and examples with no useful match.
      Compare extraction changes for complete boundaries, standalone meaning,
      relevance, distinctness, latency, and provider cost.
- [ ] Add sentence-aware boundaries. Prefer complete openings and endings, use
      pauses where helpful, and preserve the requested duration range and original
      video timestamps.
- [ ] Rank candidates with an explicit rubric for hook strength, standalone
      context, and payoff. Validate structured scores and evaluate whether they
      improve actual selections rather than treating model scores as objective.

## Better context and variety

- [ ] Reject or expand setup-heavy excerpts that depend on missing context,
      unexplained pronouns, or earlier references. Keep enough introduction for
      the clip to make sense on its own without inventing context.
- [ ] Make transcript windows sentence-aware and include neighboring context so
      moments that cross window boundaries are not missed or cut awkwardly.
- [ ] Add meaning-based deduplication across the whole video. Avoid several clips
      making the same point even when their timestamps do not overlap; retain
      distinct perspectives and topics.
- [ ] Offer two cuts of a promising moment: a short, punchy version and a longer
      version with more context. Let users compare and choose before creating or
      exporting clips.

## Audio, visuals, and framing

- [ ] Use audio and visual cues to find reactions, laughter, emphasis, and funny
      moments that transcript-only selection can miss. Evaluate the added quality,
      processing time, and cost before making this a default.
- [ ] Suggest portrait crop or blurred background based on speaker placement and
      important visuals. Preserve multiple speakers, screen content, and captions;
      keep framing suggestions editable.

## Personalization

- [ ] Learn from clips a user keeps, rejects, edits, or exports to improve future
      suggestions for that account. Make feedback controls clear, allow resetting
      preferences, and evaluate improvements against an unpersonalized baseline.

Suggested order: establish the evaluation set, then implement sentence-aware cuts
and explicit quality ranking before adding more complex signals.
