# Initial clip selection review

On 2026-10-30, six saved excerpts from two local Greek-language projects were
read alongside their generated titles and reasons. This was a transcript-only
editorial inspection, without playback or additional provider calls. The original
media, full transcripts, and project identifiers are not included here.

| Source | Saved source ranges inspected | Observations |
| --- | --- | --- |
| Approximately 79-minute live/reaction video | 324–374 s, 1257–1291 s, 1471–1515 s | Some explanations claim clear escalation, a complete story, or a punchline. The transcript alone sometimes has abrupt topic changes, unclear references, or garbled words. Intensity does not establish a self-contained joke. |
| Approximately 36-minute conversational visit | 101–138 s, 149–200 s, 495–539 s | A car-rating exchange reaches an explicit rating; a housing discussion reaches a clear reason for avoiding rent. Another excerpt shifts from introductory chatter into driving commentary. Standalone clarity and relevance to a particular brief should be judged separately. |

These observations suggest reviewing the actual excerpts rather than relying on
candidate titles and reasons. They do not establish that any individual clip is
bad: audio delivery and visuals may contribute meaning that the transcript lacks.

## Implemented response

- Use the same hook, context, payoff, and brief-relevance rubric during extraction
  and review.
- Supply actual, boundary-refined excerpt text to the review pass.
- Validate complete 0–5 ratings and candidate references, reject malformed reviews,
  and remove selected candidates below the documented thresholds.
- Permit fewer results and group repeated points even across nonoverlapping times.
- Limit review requests to 20 candidates and compare survivors across batches.

Automated tests use stubbed provider responses. They verify filtering, data flow,
deduplication enforcement, bounded batches, cancellation, and response validation.
They do not verify the model's editorial accuracy. No new extraction was run on
these local projects and no saved clips were changed during this review.

## Remaining evaluation

Build a consented evaluation set with interviews, podcasts, talks, and reactions
in multiple languages, including clean speech, noisy transcripts, repeated points,
and no useful match. For fixed source ranges and briefs, compare the previous
and current selections without showing reviewers which system produced them.
Record complete boundaries, standalone context, hook, payoff, brief relevance,
distinctness, kept/edited/rejected decisions, request count, latency, and actual
provider usage. Include single-candidate cases, which skip the review call, and
large pools that require multiple review batches.

Do not treat the model's own ratings or the passing automated suite as evidence
of better real-world selections. The thresholds and batching strategy remain
editorial choices to evaluate against those human reviews.
