# Long video → Shorts

Open **Long video → Shorts** from the creation tools to see your project library.
Search by project name or filter by ready, processing, or needs-attention status.
Cards show the source type, duration, saved clip count, ready export count, and date.
Choose **New project** to import a video; **Back to projects** returns to the library.
Upload an MP4, MOV, WebM,
or M4V video with spoken audio, up to 1 GB, two hours, and 3840 pixels per dimension.
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
Choose 1–10 suggestions and a preferred duration range between 10 and 180 seconds.
The source must be at least as long as the requested minimum.

Expand **Process only part of the video** to set optional start/end times in seconds.
The default is the whole video. Leaving the end blank uses the end of the source.
Only the chosen range is sent for transcription and highlight selection; timestamps
stay on the original source timeline. The range must fit the video and be at least
as long as the minimum clip length. YouTube ranges are checked after downloading
metadata. Downloads and previews still cover the full source and retain existing limits.

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
3. In **Clips**, review the suggested titles and explanations, or add a clip manually.
   The clip list stays beside the editor on desktop and scrolls horizontally on phones.
4. Open **Preview & edit**. Adjust start/end times or select boundaries from transcript words.
5. Choose a portrait crop with horizontal positioning, or preserve the picture over a blurred background.
6. Correct caption words and timing, choose a font/style, and save.
7. Export individual clips or select several and use **Export selected**. Download each finished file.

Exports are 720 × 1280 H.264/AAC MP4 at 30 fps. Every clip is one continuous excerpt
of the original video with its original audio. Captions can be disabled. A project
can contain up to 20 clips, each at most 180 seconds. Changing clip boundaries
rebuilds its captions from the source transcript; review corrections after trimming.
Saving changes to picture, timing, or captions invalidates that clip's previous export;
title-only and unchanged saves preserve it. Other clips remain unchanged.

Audio is sent to OpenAI (`whisper-1`) for transcription using the existing service
or personal key selection. Transcript windows are sent to the configured text model
(`DEFAULT_GPT_MODEL`) for suggestions. Both use existing AI usage tracking. Model
responses must identify real word indices; invalid ranges and near-duplicate
suggestions are discarded. Larger candidate sets receive a final ranking pass.

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
