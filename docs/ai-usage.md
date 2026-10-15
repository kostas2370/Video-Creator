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
Known totals can be partial when a provider omits measurements. Voice characters,
images, and video seconds are separate units, not converted into text tokens.
These measurements are not prices, account balances, or invoices. Interrupted
streams and failed provider requests may incur charges that the app cannot measure.
Web image searches, uploads, and local rendering are excluded.

Records contain no prompts, generated text, credentials, or response bodies.
Database errors while saving usage are logged without failing successful generation.

Provider response references:
[Chat streaming usage](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events)
and [image usage](https://developers.openai.com/api/reference/resources/images/methods/generate).
