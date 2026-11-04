# Diagram icons

Install the catalog after applying migrations:

```sh
python manage.py migrate
python manage.py download_icons
```

The command downloads the complete Lucide and Material Design Icons collections
from Iconify's icon-sets repository. It imports concrete SVG paths, skips aliases,
hidden icons and unsupported markup, and stores metadata in the `Icon` table.
Use `--collections lucide` to install one collection, or `--limit 20` for a small
trial. Running it again updates metadata without duplicating icons or re-enabling
icons an administrator disabled.

Artwork and collection license notices are saved under
`MEDIA_ROOT/media/icons/`, which is ignored by Git. Back up that directory with
the database. Only the downloader, schema and application code belong in Git.
The API and render workers must share the same media storage.

With AI scene editing enabled, the backend searches installed icon names and
descriptions (including upstream categories where provided) using the generation
request text. It weights name matches more strongly and includes common fallback
icons. At most 60 candidates are added to the existing script prompt. GPT chooses
an optional ID for each diagram item; it does not receive the whole catalog and
makes no separate icon-search API call. This is keyword search, not semantic
search: synonyms and abstract concepts may be missed. GPT may omit an icon;
unknown, disabled or missing artwork is omitted during validation.

The authenticated `/api/icons/` endpoint supports paginated `search` and exact
`keys` lookups. Each diagram item has a searchable picker for replacing or removing
its icon. Preview and export use the same local artwork and layout. The render
image's FFmpeg includes the librsvg decoder used for these SVG inputs.

Choose **Icon graph** for horizontal icon-to-icon arrows, branches and merges,
without cards. Graphs support 2–6 items and up to 8 directed connections. Each
connection references zero-based `source` and `target` item indices and an optional
`label`. Omitting `connections` draws a horizontal chain; an empty array draws no
arrows. The editor preserves connection targets when removing an item and prevents
self-connections, duplicate arrows and loops. Cyclic graphs are not supported.
Nodes are laid out automatically in columns. Arrows route around skipped columns;
moving markers follow the routed paths at constant speed in preview and export.
Keep portrait graphs to 2–4 nodes and short labels when possible for readability.

Lucide uses ISC and Material Design Icons uses Apache 2.0. The downloader retains
each collection's license notice and records its license URL and author in the
table/API. Keep those notices with distributed artwork.
