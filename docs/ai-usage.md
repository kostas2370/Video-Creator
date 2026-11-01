# AI usage tracking

The authenticated **Usage** page (`/usage/`) shows each user's consumption by
service, provider, model, and personal/service API keys. The API is
`GET /api/usage/?period=7|30|all` (default: 30 rolling days).

Usage tracking belongs to `apps/usage`: `models.py` owns `AIUsage`, `services.py`
records measurements, `tokens.py` normalizes provider counts, and `querysets.py`
aggregates reports. Filters, serializers, views, and the existing `/api/usage/`
route live in the same app. Provider integrations call `apps.usage.services.record_usage`.

Run `python manage.py migrate` and restart backend workers when deploying.
The app-move migrations adopt the existing `videomanagement_aiusage` table without
copying or dropping records. They also retain content-type IDs, permission grants,
and admin history. The table name is kept intentionally for compatibility; future
usage model changes belong to the `usage` app. No historical consumption is
reconstructed, and recording/reporting behavior stays the same.

Generation has no internal application credit balance. The usermanagement migration
`0008_remove_generation_credit_balance` removes stored legacy balances; generation,
scene edits, and drafts no longer reserve, deduct, or refund them. Provider credentials,
upstream quotas, authentication, ownership checks, and request throttling still apply.

- GPT (including vision), Claude, and Gemini record provider-reported tokens.
  GPT streaming requests include usage and accept the final empty-choices chunk.
  Completed script retries each produce a record. Claude input counts include
  cache reads/writes; Gemini totals preserve the provider's reported total.
- OpenAI image generation and edits record reported tokens and image counts.
  Stable Diffusion, Midjourney, and custom image providers record image counts.
- OpenAI `tts-1`, ElevenLabs, 60dB, and custom TTS record input characters.
- Completed Sora jobs record generated seconds. Custom video generation records
  request counts, without an assumed duration.

Missing token measurements remain null, and the page labels them unavailable.
Each token metric has its own reporting count; partial coverage is shown on both
the summary card and individual table columns. No requests in a period gives zero
totals; requests without a measurement give null for that metric.
Known totals can be partial when a provider omits measurements. Voice characters,
images, and video seconds are separate units, not converted into text tokens.
These measurements are not account balances or invoices. Interrupted
streams and failed provider requests may incur charges that the app cannot measure.
Web image searches, uploads, and local rendering are excluded.

Records contain no prompts, generated text, credentials, or response bodies.
Database errors while saving usage are logged without failing successful generation.
Custom visual providers are recorded once the upstream response provides a media
URL or a successful binary response, before download, conversion, or file saving.
JSON responses can supply a standard `usage` object for token normalization.

## Generation cost estimates

AI creation shows a scenario/script estimate before **Draft storyboard**.
Storyboard review shows an estimated USD generation cost before **Proceed**,
including the scenario cost already incurred and the planned media costs. The
estimate updates with unsaved narration and shot-duration edits. Scene controls
also show estimates before generating a replacement visual, preparing a starting
image, animating an approved image, or regenerating narration. Looking up an
estimate makes no provider request and does not save the script or start generation.
An unavailable estimate does not prevent generation.

The breakdown separates scenario/script, images, animation, and narration.
Scenario estimates use the assembled prompt, an approximate range of two to four
characters per input token, expected output by scene count, and the configured
output budget, including OpenAI reasoning allowance. This planning range is not a
guaranteed bound; reference inputs, language, series context and retries can change it. Character video projects
include starting-image preparation and later animation as separate line items;
animation is charged only when explicitly requested. Narrated clip durations use a
150-words-per-minute planning assumption until narration audio exists. Known built-in
video providers use the same duration rounding and limits as generation.

Built-in rates were checked on **1 November 2026**:

- OpenAI scenario rates include `gpt-5.4-mini`, `gpt-5.4`, `gpt-5.4-nano` and
  `gpt-5.5`, using their official model pages linked from the cost breakdown.
  Other script models use configured rates or remain unavailable.
- OpenAI `tts-1` uses the published per-character rate from its
  [model page](https://developers.openai.com/api/docs/models/tts-1).
- GPT Image 2, GPT Image 1.5, and GPT Image 1 Mini use output-only reference-price
  ranges by quality from the [image guide](https://developers.openai.com/api/docs/guides/image-generation).
  These compare the guide's 1024-square and 1024×1536/1536×1024 sizes; they are not
  bounds or quotes for the project's exact frame. Text and image inputs cost extra.
  Automatic quality and unknown models remain unpriced.
- Runway `gen4.5` uses its [API list price](https://dev.runwayml.com/pricing).
- Other providers and models remain **Price unavailable** until configured.
  Unknown line items are excluded from the clearly labeled known subtotal. When
  all prices are unknown, the total is unavailable, rather than zero.

The **Usage** page shows cost estimated from completed requests, with coverage
counts when only some requests have a price. Prices are saved on new usage
records; later rate changes do not reprice them. GPT Image 2 recorded costs require
separate reported text/image input counts and output tokens and use the
[token rate card](https://developers.openai.com/api/docs/pricing), without cache
discounts. Missing measurements stay unpriced. Earlier usage is not backfilled.

Open **Project extras → Generation costs** to compare the saved storyboard generation
estimate with recorded scenario and media costs. The original estimate is captured
at storyboard approval or the first generation pass and preserved on resume. Recorded project
usage includes subsequent replacements and measured retries, including provider
successes followed by local saving failures. Association is set around each media
provider call, including calls in generation threads, and checked against ownership.
Older requests have no project association. Scenario calls and script rewrites are linked to the project and included in the
comparison, including measured script-validation retries. Standalone media-library
generation is excluded. Existing estimates without a scenario line retain their
original media amounts and mark the earlier scenario cost unavailable. Deleting a project preserves account usage
while removing the project association and saved estimate.

These are planning estimates, not invoices or a spending cap. Additional rewrites, retries, taxes, negotiated rates and discounts are excluded
from the pre-generation estimate. Scenario drafting costs already incurred are
labeled separately so Proceed does not imply another scenario charge. Failed or
interrupted requests can incur charges without producing a measurement.

### Configuring other rates

Set `AI_COST_RATES` in `backend/.env` to a JSON object. Keys are
`service:provider:model`; service is `text`, `images`, `tts`, `video`, or `stt`.
Provider and model must match usage identifiers exactly. Custom providers use their
configured name and a blank model. Built-in visual selection names `runway`,
`kling`, `gemini-video`, `midjourney` and `stable-diffusion` map to their recorded
provider/model identifiers. Rates can override built-in entries.

```dotenv
AI_COST_RATES={"images:My image provider:":{"images":"0.04","checked_at":"2026-11-01","source":"https://example.com/pricing"},"video:My video provider:":{"requests":"0.60","checked_at":"2026-11-01"}}
```

Each value is USD per **one** unit. Supported units are `characters`, `images`,
`seconds`, `requests`, `input_tokens`, and `output_tokens`. Divide published
per-million-token prices by one million before entering token rates. Multiple
specified units are additive. Scenario token estimates are approximate; configured token rates can price both
the planning range and recorded provider usage. Recorded measurements remain
unavailable when the provider omits required counts. Custom video integrations record request counts, so use a request
rate for those; a missing duration is never priced as zero seconds. Supply a
`checked_at` date and public `source` URL for the rate's provenance.

Apply migration `usage.0003`, restart the API and generation workers, and rebuild
the frontend together when upgrading. No provider calls or historical repricing
run during the migration.

Token normalization lives in `apps/usage/tokens.py`, independently of persistence.
The default adapter accepts common token field names in dictionaries or SDK objects.
Add a `TokenUsageAdapter` to `TOKEN_USAGE_ADAPTERS` for a provider with different
field names or additive input counts; the recording function needs no new branches.
Reported totals take precedence over computed totals. A total is computed only when
both input and output counts are known, and invalid counts remain unavailable.
Anthropic cache input counts are additive only for its adapter; custom providers
use the generic format even if their display name matches a built-in provider.

Provider response references:
[Chat streaming usage](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events)
and [image usage](https://developers.openai.com/api/reference/resources/images/methods/generate).
