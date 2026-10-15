# AI usage tracking

The authenticated **Usage** page (`/usage/`) shows each user's consumption by
service, provider, model, and personal/service API keys. The API is
`GET /api/usage/?period=7|30|all` (default: 30 rolling days).

Apply migration `0028_ai_usage` and restart backend workers when deploying.
Only new requests are measured; historical usage cannot be reconstructed.

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
These measurements are not prices, account balances, or invoices. Interrupted
streams and failed provider requests may incur charges that the app cannot measure.
Web image searches, uploads, and local rendering are excluded.

Records contain no prompts, generated text, credentials, or response bodies.
Database errors while saving usage are logged without failing successful generation.
Custom visual providers are recorded once the upstream response provides a media
URL or a successful binary response, before download, conversion, or file saving.
JSON responses can supply a standard `usage` object for token normalization.

Token normalization lives in `utils/token_usage.py`, independently of persistence.
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
