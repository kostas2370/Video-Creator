# Shared music catalog and private tracks

User uploads and music imported into a video stay private to their owner. Approved
**General music** is available across accounts. Users can preview, download, and
use general tracks but cannot edit or remove them. The library collection selector
switches between private media and general music.

## Automatic music selection

In generation's advanced settings, enable **Auto-select music** to pick a soundtrack
from the general catalog after script approval. You can still leave music blank or
paste a YouTube link. The choice is saved in drafts and templates (`music="auto"`
in generation requests). If generation is resumed, missing automatic music is
retried while an existing soundtrack is preserved. Generation can finish without
music when the catalog is unavailable.

In the editor, **Project extras → Auto-select music** adds or replaces background
music immediately. Click again to try a different track when alternatives exist.
It uses the video title, genre, prompt, script, and catalog tags with keyword
matching. Unrecognized topics favor general-use music. Selection only considers
approved catalog entries with a license URL and a stored audio file. No YouTube
search, download, or AI request runs during selection. Private tracks are excluded.
If no tracks are available, the editor displays an error and keeps existing music.

`POST /music-catalog/auto-select/` accepts `{"video_id": "..."}` for an owned,
editable video and returns the selected catalog track with its attribution.

## Automatic deployment setup

`fixtures/music_catalog.json` bundles 390 YouTube music candidates with titles,
source IDs, duration, category, uploader metadata, declared license, and tags:

| Category | Tracks |
| --- | ---: |
| educational | 100 |
| suspense | 100 |
| fun | 100 |
| horror | 10 |
| general | 50 |
| commercial | 30 |

After migrations, both `startdjango.sh` and `setupdjango.sh` run:

```sh
python manage.py setup_music_catalog --best-effort
```

This reads the bundled JSON, creates shared catalog records, then uses the shared
pytubefix downloader to fetch missing audio. Deployment needs **no YouTube Data API
key**. Audio is stored under the normal media directory; persist that directory
across deployments. The first run can take time and storage for 390 audio files.

Reruns reuse source IDs, skip existing files, restore missing files, and preserve
existing approved records and edited tags. Downloaded audio must be playable, at most 15
minutes, and no larger than 50 MB before normalization. Downloads pause after three
consecutive failures. With `--best-effort`, download failures do not prevent the app
from starting; metadata and successful downloads remain for the next attempt.
YouTube bot protection, unavailable videos, and network failures can prevent some
files from downloading. This is reported rather than treated as a complete catalog.

Set `MUSIC_CATALOG_AUTO_SETUP=false` to skip automatic setup. Run it manually to
retry missing tracks:

```sh
python backend/manage.py setup_music_catalog
```

Options:

```sh
python backend/manage.py setup_music_catalog --metadata-only
python backend/manage.py setup_music_catalog --catalog /path/to/catalog.json
```

Manual setup reports download failures with a nonzero exit status. Invalid manifests
are rejected before any records are created, including with `--best-effort`.

## Discovery and snapshot refresh

The deployed catalog uses the bundled snapshot. Discovery is a separate maintenance
command. Enable YouTube Data API v3 and set `YOUTUBE_API_KEY` in `backend/.env` to
find new candidates or export the current catalog:

```sh
python backend/manage.py discover_music --export backend/fixtures/music_catalog.json
```

Discovery searches music-category videos marked Creative Commons, checks the
license field again in video metadata, and accepts durations from 30 seconds to
15 minutes. It targets the counts above and deduplicates source IDs across
categories. Complete categories make no API requests on rerun. Incomplete searches
retain saved results after quota or network errors. Widen a search if necessary:

```sh
python backend/manage.py discover_music --category suspense --pages-per-query 6
```

Categories reflect search intent. "Instrumental candidate" is a search hint, not
analysis of the recording. "Commercial" means corporate/advertising style rather
than verified commercial-use rights. Different uploads can contain the same recording.

## Automatic approval and attribution

Setup automatically approves downloaded tracks whose stored YouTube metadata
explicitly declares `creativeCommon` and identifies an uploader. It adds a license
information link and attribution containing the title, uploader, source URL, CC BY
declaration, and a note about extraction and possible edits. The metadata records
`approval_basis=youtube_declared_creative_commons` and the approval timestamp.
Existing attribution and license links are preserved. This is approval based on the
uploader's license declaration, not an independent copyright or rights review.

To approve already-downloaded entries without starting new downloads:

```sh
python backend/manage.py setup_music_catalog --approve-only
```

To download tracks while leaving new entries pending manual approval:

```sh
python backend/manage.py setup_music_catalog --no-auto-approve
```

Missing audio, a missing uploader, or a missing Creative Commons declaration keeps
an entry pending. `--metadata-only` only seeds metadata. Admin can review and adjust
source information, attribution, license URLs, and approval status. The admin form
requires an audio file and license URL before approval.

Catalog tracks live in `MusicCatalogTrack`, with their own audio, source, license,
attribution, approval, and discovery metadata. `MediaAsset` keeps only user-owned
media; catalog discovery and downloads do not create user media records. The catalog
API exposes only approved tracks with audio and a license URL.

`GET /media-assets/?kind=AUDIO` returns the user's private audio.
`GET /music-catalog/` returns approved general music, with optional `search` and
`category` filters. Its `download` and `use` actions allow authenticated users to
download or add music to their own editable videos. The catalog API does not allow
creating, editing, or deleting catalog tracks. The frontend collection selector
uses these separate APIs. Pending catalog metadata is available only in admin.

YouTube's Creative Commons flag and "no copyright" titles do not verify ownership
or permission to redistribute audio. The bundled entries are candidates, not a
verified license inventory. YouTube downloading is also subject to its platform
terms, independently of the recording's copyright license.

- [YouTube search and license filters](https://developers.google.com/youtube/data/reference/rest/v3/search/list)
- [Video metadata](https://developers.google.com/youtube/data/reference/rest/v3/videos)
- [YouTube developer policies](https://developers.google.com/youtube/terms/developer-policies)
