# Project ZIP exports

In the video editor, open **Export → Project ZIP**. The ZIP contains the editable project and its referenced media. The finished video is optional and is excluded by default. Project import is not implemented yet.

## Format version 1

`project.json` contains `format: "viddie-project"`, integer `version: 1`, `exported_at`, and these sections:

- `project`: title, description, tags, notes, prompt, supported storyboard/settings, voice description, source-audio timings, cuts, and cover settings. Media references point to ZIP-relative paths.
- `scenes`: active scenes in edit order, with text, caption alignment, motion/animation, transitions, cuts, overlays, narration/voiceover references, starting assets, and saved visual versions. Scene IDs are archive references; a future importer must create new IDs and remap dependent timing/cut identities.
- `icons`: referenced diagram icons and their attribution/license metadata. Music attribution and license/source URLs are retained when a catalog track is used.
- `files`: each packaged media path, byte size, and SHA-256 digest.

Media lives under `media/` with generated filenames. Repeated references to the same storage file produce one ZIP member. The manifest is written after the media so its checksums describe the actual exported bytes.

Credentials, owner/account records, public share tokens, internal storage paths, job state, and generation traces are not exported. Voice descriptions do not transfer provider credentials or cloned-voice access. Archived/deleted scenes are excluded.

A future importer should validate the format/version and file hashes, reject unsafe paths, remap IDs and cut/cache identities, store media under the importing account, and require selection of an available voice before regenerating narration.

## Delivery

`GET /api/videos/{id}/export-project/?check_only=true&include_output=false` performs the same permission and media availability checks as a download and returns its authenticated download URL, filename, media count, and media bytes. The UI uses this to report preparation errors and refresh authentication before starting a native browser download.

`GET /api/videos/{id}/export-project/?include_output=false` streams a ZIP64-capable attachment. Both requests require the project owner. Browser downloads use the existing access-token cookie; the URL grants no access by itself. Export is unavailable while the video is generating/rendering.

R2 media is streamed using the preflight ETag, without materializing a local media cache. ZIP media is stored without recompressing already-compressed video/audio/images; JSON is compressed. Chunked ZIP delivery avoids holding an entire media file or archive in server/browser memory. No temporary project ZIP is stored. Missing media fails preflight; media changes or a storage failure during transfer abort the download, so the incomplete file must be downloaded again. Original files are untouched.
