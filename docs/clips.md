# Long video → Shorts

Open **Long video → Shorts** from the creation tools to see your project library.
Search by project name or filter by ready, processing, or needs-attention status.
Cards show the source type, duration, saved clip count, ready export count, and date.
Choose **New project** to import a video; **Back to projects** returns to the library.
Upload an MP4, MOV, WebM,
or M4V video with spoken audio, up to 1 GB and 3840 pixels per dimension. There is no source duration cap.
Alternatively choose **YouTube link** and paste a video or Shorts URL. Imports run
in the background using the existing pytubefix dependency. They select the highest available
resolution up to 1080p that fits within 1 GB, including audio, automatically stepping
down to 720p, 480p, or lower when needed. At equal resolution, combined MP4 streams
are preferred; separate video and audio streams are joined with FFmpeg. When no
resolution fits, the import explains that a trimmed or smaller file is needed.
The same limits apply before transcription. Only canonical
YouTube video links are accepted; playlists and arbitrary URLs are rejected.
Use a video you own or have permission to edit. Private, restricted, or
YouTube-blocked downloads can fail; a file upload remains available. Retries reuse
a downloaded source rather than downloading it again.
Choose 1–10 suggestions and a preferred duration range in minutes (from 1/6 to 3 minutes). Decimal minutes are supported; 0.5 means 30 seconds.
The source must be at least as long as the requested minimum.

Expand **Process only part of the video** to set optional start/end times in minutes.
The default is the whole video. Leaving the end blank uses the end of the source.
Only the chosen range is sent for transcription and highlight selection; timestamps
stay on the original source timeline. The range must fit the video and be at least
as long as the minimum clip length. YouTube ranges are checked after downloading
metadata. Downloads and previews still cover the full source and retain existing limits.

Optionally describe the clips you want in **What kind of clips do you want?**,
for example, “Funny moments” or “Practical advice for first-time founders”.
The saved brief guides both candidate extraction and final ranking. Omitting it,
sending `null`, or leaving it blank uses the chosen clip focus. The limit is 2,000
characters. Selection remains based on spoken content.

## Selection preferences

New projects offer two controls:

- **Clip focus:** General highlights (default), Funny moments, Practical advice,
  Stories, or Debates and opinions. Focus guides extraction and review without
  replacing your written brief. A conflicting explicit request, including an AI
  transcript search query, takes priority over the preset.
- **Selection mode:** Fast skips the extra ranking review, reducing text-provider
  usage. Initial suggestions and transcription still incur normal charges, and
  repeated ideas may remain. Balanced (default) reviews pools with multiple
  candidates. Strict reviews even a single candidate with a higher acceptance
  bar; it may return fewer clips or none. Balanced and Strict add review usage.

These choices are saved with the project and shown in its workspace. Retries and
AI transcript searches use them. The controls are set when creating a project;
existing projects default to General highlights and Balanced. All modes use the
spoken transcript; none analyse video frames, voice delivery, or laughter.

The first release targets interviews, podcasts, talks, and other speech-led videos.
Highlight selection uses the transcript, not visual understanding. It may return
fewer clips than requested. Review context, meaning, caption accuracy, and framing
before sharing. There is no promise of engagement or virality.

## Workflow

1. Upload the source and choose your suggestion settings.
2. Wait for a browser-friendly preview, word-timed transcription, and highlight suggestions.
3. In **Clips**, review the suggested titles and explanations, or add a clip manually.
   The clip list stays beside the editor on desktop and scrolls horizontally on phones.
4. Open **Preview & edit**. Adjust start/end times in minutes or select boundaries from transcript words.
5. Choose a portrait crop with horizontal positioning, or preserve the picture over a blurred background.
6. Correct caption words and timing, choose a font/style, and save.
7. Export individual clips or select several and use **Export selected**. Download each finished file.

Exports are 720 × 1280 H.264/AAC MP4 at 30 fps. Every clip is one continuous excerpt
of the original video with its original audio. Captions can be disabled. A project
can contain up to 20 clips, each at most 180 seconds. Changing clip boundaries
rebuilds its captions from the source transcript; review corrections after trimming.
Saving changes to picture, timing, or captions invalidates that clip's previous export;
title-only and unchanged saves preserve it. Other clips remain unchanged.

Use the **Uploaded** checkbox on a clip card to track clips you have uploaded
elsewhere. This marker is saved per clip and can be cleared manually. Downloading
or exporting a clip does not mark it as uploaded, and changing the marker keeps
the saved export.

For YouTube sources, suitable captions are checked through pytubefix before audio
transcription. Original-language tracks with usable word offsets are preferred.
Tracks with only phrase timing, incomplete range coverage, ambiguous language, or
unavailable caption endpoints fall back to audio transcription. The workspace
shows whether the transcript came from YouTube, local Whisper, OpenAI, or a saved
transcript. Existing saved transcripts and successful chunk checkpoints are reused.

Audio transcription defaults to paid OpenAI (`whisper-1`) using existing service
or personal API keys. Suitable YouTube captions are checked first, avoiding an
audio transcription request when they can be reused. AI highlight selection still
uses the configured text provider.

Local Whisper remains optional. Set `SPEECH_TRANSCRIPTION_PROVIDER=local` and start
it with `docker compose -f backend/docker-compose.yml --profile local-whisper up -d --build whisper`.
The service uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper), the
multilingual `small` model, CPU int8 inference, and word timestamps. It has no
published host port and downloads models on first use into the persistent
`whisper-models` volume. Set `WHISPER_MODEL` and `WHISPER_CPU_THREADS` in the Compose
environment to tune it. Larger models need more RAM and take longer; benchmark
representative audio before changing models. `/health` reports service availability.

Local inference does not create paid usage records and does not automatically
fall back to the paid API on failure. `LOCAL_WHISPER_URL` defaults to
`http://whisper:9000`; `LOCAL_WHISPER_TIMEOUT` defaults to 1800 seconds per chunk,
including model loading and queued work. Non-Docker backends must point this URL
at their local service. Set `YOUTUBE_CAPTIONS_ENABLED=false` to skip caption reuse.

Transcript windows are sent to the configured text model
(`DEFAULT_GPT_MODEL`) for suggestions. Paid provider calls use existing AI usage tracking. Model
responses must identify real word indices; invalid ranges and near-duplicate
suggestions are discarded.

Selection uses a shared editorial rubric: an opening hook, standalone context,
a payoff within the spoken excerpt, and relevance to your brief. Missing setup,
garbled transcription, and unfinished punchlines count against an excerpt. A
reaction or joke must make sense in the transcript; the model cannot inspect
unseen visuals to fill in missing meaning.

In Balanced mode, when two or more candidates remain, a review pass reads their actual excerpts,
alongside their titles and reasons. It returns validated integer ratings from
0–5. Clips need at least 2 for hook and 3 for context and payoff; when a brief
or a non-general focus is present, relevance must also reach 3. Strict mode raises
the hook threshold to 3 and the other thresholds to 4, and reviews a single
candidate too. These are subjective model judgments,
not measured audience engagement, and ratings are not saved or shown as quality
guarantees. Review can return fewer clips or none. It also groups candidates
repeating substantially the same point or joke, keeping one per group even
when their timestamps do not overlap. Different perspectives can remain.

When enabled by the selection mode, review runs even when the candidate count fits the requested count. Requests
contain at most 20 candidates; larger pools are reviewed in batches, with their
survivors reviewed together. This adds text-provider usage and latency, tracked
through existing AI usage records. Fast always skips review; Balanced skips review
for zero or one candidate. Those cases rely on the extraction rubric. Deduplication covers the new candidate
pool; it does not semantically compare against previously saved clips. Existing
saved clips are preserved.

New suggestions and AI transcript search results adjust their cuts to nearby
sentence boundaries or pauses when possible. Each edge can move by up to five
seconds, while preserving the chosen duration limits and original source
timestamps. Refinement checks the full saved transcript, including context across
AI window edges. It prefers two clean edges, then preserving selected speech,
then the smallest adjustment. If completing both edges cannot fit, it can still
fix one edge or trim to a nearby complete sentence. Already clean edges stay put.
This uses transcript punctuation (including Greek question marks) and word timing;
review the result because a natural boundary does not guarantee complete context.
Existing saved clips and manual trims are unchanged, and refinement makes no
additional provider requests.

## Full source transcript

Open **Transcript & AI search** on the project page to read the entire saved
source transcript without opening a clip. Search filters the displayed passages;
**Copy full transcript** and **Download TXT** always include all passages and their
source timestamps. This view does not change when individual clip captions are edited.

## Find clips by description

Open **Transcript & AI search** and use **Find clips with AI**. Describe a topic or moment,
for example, “Find a clip where they explain how to start a business”. Search uses
the saved transcript and the project's preferred clip lengths. It returns up to
three candidate excerpts without changing the original extraction brief or adding
clips automatically. Choose **Add and edit clip** to create a result and open it
in the editor. No match and provider errors leave the query available for retry.
Text-provider usage is charged; no transcription request is made for search.

You can switch between clip editors while keeping each unsaved draft. A successful
save closes that editor; closing without saving discards that clip's draft.
Timestamp inputs accept the full precision of generated word boundaries.
Keep decimal timestamps from AI search results when adding or editing a clip;
there is no need to round them to whole seconds. Caption boundaries handle tiny
decimal rounding differences, including in previously saved clips.

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
checkpoints. Up to two requests run concurrently per project. Completed chunks are
saved by index even when they finish out of order, and the final transcript is
merged in source order. If one request fails, no further chunks are dispatched;
requests already running finish and their successful results are saved. Retries
only send missing chunks, including when older sequential checkpoints are present. A retry reuses the saved preview, completed chunks, and full transcript.
New imports also reuse completed source transcripts from existing projects owned
by the same user when the source identity matches and the saved range covers the
new range. Uploads match by SHA-256 content, independent of filename; YouTube links
match by canonical video identity across downloaded qualities. Legacy sources are
indexed lazily. Words are copied with original timestamps and clipped to the chosen
range, so deleting the older project does not remove the new transcript. Partial
checkpoints are reused only within their original project. Concurrent first imports
may still transcribe independently; deleting every matching project removes reuse.
A failure while finding highlights does not remove manual clips or the upload.
Retry suggestions add non-overlapping clips while preserving existing edits.
Exports have independent statuses, job tokens, and retries. Batch dispatch reports
per-clip queue failures. Duplicate deliveries and superseded tokens cannot commit
results. Source processing idle for three hours can be retried. Exports become retryable
after 30 minutes, with a scheduled reaper checking once a minute and publishing
status changes. Old job tokens cannot commit results after recovery.

Project and clip API routes require authentication and filter by owner. Source files, previews, and exports live in private filesystem storage outside
the public media directory. Their API URLs require ownership and cookie or bearer
authentication, support single byte-range requests for seeking, and disable shared
caching. Old `/media/clips/` URLs return 404 in nginx and Django development mode.
The storage migration moves existing clip files, preserving their database names. Deleting a project removes its
upload, preview, clips, and exports through the existing file cleanup integration.

## Deployment

The feature lives in the dedicated Django app `apps.clips`, with `/api/clips/`
routes and `/clips/` frontend pages. It reuses caption word validation, transcription,
caption styles, ASS composition, font handling, provider credentials, and usage.

Selection preferences add migration
`0008_clipproject_clip_focus_clipproject_selection_mode`. Apply migrations, restart
the API and workers, and rebuild the frontend to expose the new controls. No
provider calls or clip regeneration are performed by this migration.

Pause uploads and workers before running `python manage.py migrate` so files are
not written to public storage during the move. Then restart the API, general
worker, render worker, and Beat, and rebuild the frontend. Back up the private
clip folder alongside the database. `CLIP_STORAGE_ROOT` optionally overrides its
default of `backend/private-clips`; keep it outside publicly served directories.
Rolling back the migration does not move private files back into public storage. The frontend nginx configuration allows 1025 MB request
bodies only under `/api/clips/`; other upload limits are unchanged. Additional reverse
proxies must also allow the source upload size and a suitable upload timeout.

Project pages subscribe to the existing authenticated server-event infrastructure.
Events contain only an invalidation signal; a lightweight progress endpoint omits
transcripts and caption words. The page fetches only changed clips and loads the
source transcript once it becomes available. Reconnect, focus, and explicit refresh
reconcile missed events while retaining unsaved editor and hashtag drafts.
Clip responses expose their update timestamp as `revision`; send it back when
saving edits. Clips omit the duplicate `updated_at` field. Project responses
continue to use `updated_at`.

General workers process downloads, previews, transcription, and suggestions. The `renders`
queue processes exports. Processing has a two-hour task limit; each export has a
20-minute task limit. The processing endpoints share a ten-per-hour user allowance
with the existing superuser exemption. No providers are called during tests.

Automatic speaker tracking, split-screen layouts, silence removal, ZIP downloads,
and direct publishing are future work.

Extraction quality improvements are tracked in
[the clip extraction TODOs](clip-extraction-todo.md).
