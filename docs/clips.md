# Long video → Shorts

Open **Long video → Shorts** from the creation tools. Upload an MP4, MOV, WebM,
or M4V video with spoken audio, up to 1 GB, two hours, and 3840 pixels per dimension.
Choose 1–10 suggestions and a preferred duration range between 10 and 180 seconds.
The source must be at least as long as the requested minimum.

Optionally describe the clips you want in **What kind of clips do you want?**,
for example, “Funny moments” or “Practical advice for first-time founders”.
The saved brief guides both candidate extraction and final ranking. Omitting it,
sending `null`, or leaving it blank uses general highlights. The limit is 2,000
characters. Selection remains based on spoken content.

The first release targets interviews, podcasts, talks, and other speech-led videos.
Highlight selection uses the transcript, not visual understanding. It may return
fewer clips than requested. Review context, meaning, caption accuracy, and framing
before sharing. There is no promise of engagement or virality.

## Workflow

1. Upload the source and choose your suggestion settings.
2. Wait for a browser-friendly preview, word-timed transcription, and highlight suggestions.
3. Review the suggested titles and explanations, or add a clip manually.
4. Open **Preview & edit**. Adjust start/end times or select boundaries from transcript words.
5. Choose a portrait crop with horizontal positioning, or preserve the picture over a blurred background.
6. Correct caption words and timing, choose a font/style, and save.
7. Export individual clips or select several and use **Export selected**. Download each finished file.

Exports are 720 × 1280 H.264/AAC MP4 at 30 fps. Every clip is one continuous excerpt
of the original video with its original audio. Captions can be disabled. A project
can contain up to 20 clips, each at most 180 seconds. Changing clip boundaries
rebuilds its captions from the source transcript; review corrections after trimming.
Saving edits invalidates that clip's previous export. Other clips remain unchanged.

Audio is sent to OpenAI (`whisper-1`) for transcription using the existing service
or personal key selection. Transcript windows are sent to the configured text model
(`DEFAULT_GPT_MODEL`) for suggestions. Both use existing AI usage tracking. Model
responses must identify real word indices; invalid ranges and near-duplicate
suggestions are discarded. Larger candidate sets receive a final ranking pass.

## Full source transcript

Expand **Full video transcript** on the project page to read the entire saved
source transcript without opening a clip. Search filters the displayed passages;
**Copy full transcript** and **Download TXT** always include all passages and their
source timestamps. This view does not change when individual clip captions are edited.

## Hashtags

Each clip has a **Hashtags** panel. Generate suggestions from that clip's saved
transcript and title, review or edit them, then save. Generation uses the configured
text provider and normal usage tracking; it does not save automatically. You can
also enter hashtags manually without a provider call and copy the current draft.
Up to 20 English hashtags are supported; # prefixes and duplicates are normalized.
Topic words are translated into English and proper names use conventional English
ASCII spellings. Generation includes name hashtags for people or fictional characters
clearly featured in or central to the clip when supported by its title or transcript.
It does not identify unnamed faces. Non-ASCII generations receive one correction
attempt; invalid results are rejected without saving. Saving hashtags does not invalidate an export or alter other
clip edits. Concurrent saves reject stale metadata rather than overwriting it.
Existing clips start with an empty list. Suggestions do not claim current trend data.

## Recovery and storage

Transcription is processed in ten-minute chunks with a small overlap and saved
checkpoints. A retry reuses the saved preview, completed chunks, and full transcript.
A failure while finding highlights does not remove manual clips or the upload.
Retry suggestions add non-overlapping clips while preserving existing edits.
Exports have independent statuses, job tokens, and retries. Batch dispatch reports
per-clip queue failures. Duplicate deliveries and superseded tokens cannot commit
results. Jobs idle for three hours can be retried from the workspace.

Project and clip API routes require authentication and filter by owner. Files use
Viddie's existing media storage and serving model; deployments serving `/media/`
publicly must treat direct file URLs as shareable. Deleting a project removes its
upload, preview, clips, and exports through the existing file cleanup integration.

## Deployment

The feature lives in the dedicated Django app `apps.clips`, with `/api/clips/`
routes and `/clips/` frontend pages. It reuses caption word validation, transcription,
caption styles, ASS composition, font handling, provider credentials, and usage.

Run `python manage.py migrate`, restart the API, general worker, and render worker,
and rebuild the frontend. The frontend nginx configuration allows 1025 MB request
bodies only under `/api/clips/`; other upload limits are unchanged. Additional reverse
proxies must also allow the source upload size and a suitable upload timeout.

General workers process previews, transcription, and suggestions. The `renders`
queue processes exports. Processing has a two-hour task limit; each export has a
20-minute task limit. The processing endpoints share a ten-per-hour user allowance
with the existing superuser exemption. No providers are called during tests.

Automatic speaker tracking, split-screen layouts, silence removal, URL importing,
ZIP downloads, and direct publishing are future work.
