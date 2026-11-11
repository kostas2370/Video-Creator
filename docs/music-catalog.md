# Shared music catalog and private tracks

User uploads and music imported into a video stay private to their owner. Approved
**General music** is available across accounts. Users can preview, download, and
use general tracks but cannot edit or remove them. The library collection selector
switches between private media and general music.

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
review decisions and edited tags. Downloaded audio must be playable, at most 15
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

## Review and publish

New catalog items remain unapproved even after their audio is downloaded. They are
hidden from the user library until reviewed. In Django admin, filter Media assets
for shared, unapproved items. Verify the recording's rights and license, add the
reviewed license URL and required attribution, correct tags, then enable
`catalog_approved`. The admin form requires a file and license URL before approval.

Shared items are ownerless audio. The user API exposes only approved shared audio
with a file and license URL, alongside the user's own private media. Creating or
updating a user library item cannot change sharing or licensing metadata.

`GET /media-assets/?kind=AUDIO` returns both collections. Add `scope=private` or
`scope=shared` to filter them. Pending catalog metadata is available only in admin.

YouTube's Creative Commons flag and "no copyright" titles do not verify ownership
or permission to redistribute audio. The bundled entries are candidates, not a
verified license inventory. YouTube downloading is also subject to its platform
terms, independently of the recording's copyright license.

- [YouTube search and license filters](https://developers.google.com/youtube/data/reference/rest/v3/search/list)
- [Video metadata](https://developers.google.com/youtube/data/reference/rest/v3/videos)
- [YouTube developer policies](https://developers.google.com/youtube/terms/developer-policies)
