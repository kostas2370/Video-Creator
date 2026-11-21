# Performance check — 11 October 2026

## Frontend transfer optimization — 21 November 2026

Production builds now precompress static web assets and TrueType preview fonts at
gzip level 9. nginx serves the compressed copies to compatible clients, avoiding
per-request compression, and caches preview fonts for seven days. Originals remain
available; no glyphs, image quality, or application behavior were removed.

Measured on the local production build:

| Assets | Previous transfer bytes | Precompressed bytes | Reduction |
| --- | ---: | ---: | ---: |
| All preview fonts | 4,574,200 | 2,388,467 | 47.8% |
| All JavaScript and CSS | 528,186 | 456,515 | 13.6% |

The JavaScript/CSS baseline uses nginx's default gzip level 1 on the same build;
fonts previously had no compression configured. These totals describe the complete
asset set, not one page load. Pages and fonts still load on demand. Compressed copies
add approximately 2.7 MiB to build storage. There are no new dependencies.

Verified compression round trips against the built assets, nginx configuration,
and actual compressed/uncompressed font responses plus uncached compressed HTML
in an isolated frontend container. No page-load latency, concurrent-user capacity,
or generation/rendering speed improvement is claimed from these byte counts.

Rebuild and recreate the frontend container to enable the change. Development and
Vite preview servers retain their existing serving behavior.

## Backend query checks — 11 October 2026

The query structure is suitable for further small-deployment testing after the
fixes below. Production throughput and concurrency have not been load-tested.

## Measured improvements

| Scenario, 20 scenes | Before | After |
| --- | ---: | ---: |
| Video detail with intro and outro | 6 | 3 |
| Save video title and return editor data | 48 | 7 |
| Reorder scenes and return editor data | 56 | 14 |
| Render pipeline with mocked encoding | 27 | 8 |

These are database query counts from isolated Django tests on SQLite, with an
already authenticated user. The reorder scenario includes one query to prepare
the submitted scene IDs. They are not HTTP latency or production database benchmarks.
After the changes, counts remain constant between 2 and 20 scenes. Rendering still
performs CPU work and file processing proportional to scene count.

Changes: preload intro/outro for detail reads, reload edited video responses with
related models and scene images loaded in batches, compare ownership IDs without
fetching the owner, and prefetch scene images before rendering. Reloading after
edits avoids returning relations cached before the edit.

All 846 backend tests passed, including new query-scaling regression checks and
existing ownership, editor, preview, and rendering tests.
Eight frontend tests and the production build passed. A live silent-scene update
returned HTTP 202, completed in Celery, and was retrieved through Redis-backed
polling; the video returned to READY. Temporary smoke-test data was removed.

## Existing strengths

- Video lists join music and prompt and default to 12 results per page.
- Video detail and preview prefetch scenes and their images.
- Preview serialization already has coverage verifying no extra database queries
  after related models are loaded.
- Media timing metadata is cached, keyed by file size and modification time.
- Generation, rendering, and scene creation run as background jobs.
- Scene reordering and voice imports use bulk database updates.

## Remaining capacity concerns

1. The configured Celery solo worker runs one job at a time. Long renders also
   delay generation and auxiliary jobs. Separate rendering and generation queues,
   then size their workers against measured CPU/GPU memory and provider limits.
2. Voice changes that regenerate narration and scene drafting still perform
   provider calls synchronously. Slow providers can occupy those API requests.
   Direct scene edits, rewrites, and image regeneration now return a queued job
   immediately and execute in Celery. Status and results use the existing Redis
   result backend; signed job tokens bind polling to the owner-authorized scene.
   No separate scene-job model or refund handling is needed. Results expire after
   24 hours. The frontend polls the owner-protected operation endpoint.
3. Asset libraries now default to 24 results per page, and both asset and video
   pagination cap requests at 100. Library pages have pagination controls and
   asset selectors offer load-more controls. Large video scripts still increase
   the size of each video-list response.
4. The current stack uses SQLite and process-local memory caching. Verify with the
   actual production database and consider shared metadata caching when running
   multiple API processes.
5. Video lists filter by owner and sort by creation time. The local SQLite plan
   uses the owner index and a temporary sort. Assess a combined owner/creation-time
   index with production-sized data and the production database's query plan.
6. Rendering uses eight encoding threads and can consume substantial memory.
   Increasing worker concurrency without measuring resources can make throughput
   worse or exhaust memory.

Before choosing a supported user count, load-test list, detail, preview, and edits
against realistic media sizes, alongside simultaneous generation/render jobs.
Measure response latency, database query time, queue wait, render duration, memory,
and disk consumption. No specific concurrent-user capacity is established here.
