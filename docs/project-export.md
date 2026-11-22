# Project ZIP export and import

In the video editor, open **Export → Project ZIP**. The ZIP contains the editable project and its referenced media. The finished video is optional and is excluded by default. Use **My videos → Import project** to restore a ZIP as a new private project.

## Format version 1

`project.json` contains `format: "viddie-project"`, integer `version: 1`, `exported_at`, and these sections:

- `project`: title, description, tags, notes, prompt, supported storyboard/settings, voice description, source-audio timings, cuts, and cover settings. Media references point to ZIP-relative paths.
- `scenes`: active scenes in edit order, with text, caption alignment, motion/animation, transitions, cuts, overlays, narration/voiceover references, starting assets, and saved visual versions. Scene IDs are archive references; import creates new IDs and remaps dependent timing/cut identities.
- `icons`: referenced diagram icons and their attribution/license metadata. Music attribution and license/source URLs are retained when a catalog track is used.
- `files`: each packaged media path, byte size, and SHA-256 digest.

Media lives under `media/` with generated filenames. Repeated references to the same storage file produce one ZIP member. The manifest is written after the media so its checksums describe the actual exported bytes.

Credentials, owner/account records, public share tokens, internal storage paths, job state, and generation traces are not exported. Voice descriptions do not transfer provider credentials or cloned-voice access. Archived/deleted scenes are excluded.

## Import

`POST /api/videos/import-project/` accepts a multipart `file` and returns the new project's `id` and `title`. Authentication is required. The uploaded ZIP and total unpacked contents must each fit within 1 GB. There are at most 10,000 media files, 500 scenes, and a 5 MB JSON manifest.

Import validates version 1, the manifest schema, unique references, member paths, sizes, CRCs, SHA-256 hashes, and decoded media before writing persistent files. It rejects symlinks, encryption, unexpected members, active content, and network/playlist media formats. Files are read into bounded temporary disk storage without extracting ZIP paths. They are copied under a generated storage prefix, using the configured local or private R2 storage. Temporary files are removed afterwards. A failed database restore rolls back records and requests cleanup only for media created by that attempt. Cleanup follows the configured storage retention policy: local storage removes these new files, while R2 currently retains both copies for recovery. Existing files are never deleted.

Every import creates a new owned project, prompt, scenes, resources, and private diagram icons. Shared file references remain deduplicated. Archive IDs only remap references; they never select or modify existing records. Caption identities and valid full-timeline cut keys are rebuilt for the new media and IDs. Older archives without intro/outro reference IDs keep those full-timeline cuts stale for review. Scene cuts retain their duration checks. Optional finished output is restored as a previous export; the project opens ready to edit and re-render.

Settings pass through the editor's validators and an explicit allowlist. Credentials, public shares, job state, favorites, and owner identity are excluded. Voice access is not restored: select an available voice in Settings before regenerating narration. Diagram and music attribution/license metadata is retained; imported music is not automatically approved for the shared catalog. Archives with unsupported formats or media must be corrected or exported again.

## Delivery

`GET /api/videos/{id}/export-project/?check_only=true&include_output=false` performs the same permission and media availability checks as a download and returns its authenticated download URL and filename. The UI uses this to report preparation errors and refresh authentication before starting a native browser download.

`GET /api/videos/{id}/export-project/?include_output=false` streams a ZIP64-capable attachment. Both requests require the project owner. Browser downloads use the existing access-token cookie; the URL grants no access by itself. Export is unavailable while the video is generating/rendering.

R2 media is streamed using the preflight ETag, without materializing a local media cache. ZIP media is stored without recompressing already-compressed video/audio/images; JSON is compressed. Chunked ZIP delivery avoids holding an entire media file or archive in server/browser memory. No temporary project ZIP is stored. Missing media fails preflight; media changes or a storage failure during transfer abort the download, so the incomplete file must be downloaded again. Original files are untouched.
