# Built-in AI video providers

Choose **AI-generated visuals** and select Kling O3, Runway Gen-4.5, or Gemini
Omni Flash in the generation form. All three return video clips through the
existing storyboard, narration, preview, and render workflow. They also support
replacement visuals from **Edit visual → Generate with AI**.

| Selection | API/model | Credential |
| --- | --- | --- |
| Kling O3 · fal.ai | fal-ai/kling-video/o3/pro/reference-to-video | fal.ai key |
| Runway Gen-4.5 | gen4.5, text_to_video or image_to_video | Runway API key |
| Gemini Omni Flash | gemini-omni-1.1-flash, Interactions API | Existing Gemini key |

## Setup

For service keys, configure FAL_KEY, RUNWAY_API_KEY, and/or GEMINI_API_KEY in
backend/.env. For personal keys, open **API keys**, turn off service keys, and
save the appropriate keys. Gemini's existing key is shared by script and video
generation. Personal keys are encrypted in storage and masked in API responses.
An empty personal key does not fall back to a service key.

Apply migration apikeysmanagement.0011_video_provider_keys, restart the API and
Celery workers, and rebuild the frontend. No additional SDK is required.

## References, timing, and audio

Upload an optional PNG, JPEG, or WebP reference. It guides the first shot. Later
shots use the previous clip's last visible frame, including narration trimming.
Shared **Character & setting continuity** guidance accompanies each AI request.
These are independent generations guided by opening frames; they are not native
video extensions and do not guarantee identical character appearance.

The worker waits for queued Kling/Runway jobs, downloads the output, and validates
and normalizes it to MP4. Gemini uses synchronous Interactions generation, then
waits for its output file to become available when URI delivery is returned.
Polling has a 15-minute deadline; HTTP requests have separate timeouts. An expired
wait does not cancel an upstream job: check the provider dashboard before retrying
because the provider may still charge for it.

Kling requests 3–15 seconds, and Runway 2–10 seconds, rounded up to cover narration.
Longer narration uses the existing final-frame hold. Gemini's duration is prompted,
rather than guaranteed; usage records use the observed generated duration.
Portrait requests use portrait output. Kling supports square output. Runway
text-to-video and Gemini generate landscape for square projects, which the existing
renderer crops to square; Runway image-to-video supports square directly.

Kling requests native audio. Gemini includes generated audio; Runway Gen-4.5 may
return silent footage. With narration enabled, the app uses its separate narration.
With narration disabled, available generated clip audio is retained.

Runway limits the complete prompt to 1,000 UTF-16 characters, including style,
continuity guidance, and shot instructions. Overlong prompts fail before submitting
a paid job; shorten the individual visual prompt or shared continuity text. Prompts
are never silently truncated.

This integration uses provider defaults rather than exposing model selection,
multi-image character assets, or native video extension controls. Each provider
requires a funded account with model access. Automated tests mock provider calls;
no paid generation or visual-quality comparison is part of the test suite.

## API references

- [Kling O3 reference-to-video](https://fal.ai/models/fal-ai/kling-video/o3/pro/reference-to-video/api)
- [fal queue lifecycle](https://fal.ai/docs/documentation/model-apis/inference/queue)
- [Runway API reference](https://docs.dev.runwayml.com/api/)
- [Runway getting started](https://docs.dev.runwayml.com/guides/using-the-api/)
- [Gemini Omni Flash](https://ai.google.dev/gemini-api/docs/omni)
