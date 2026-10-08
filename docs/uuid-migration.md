# UUID identifiers

Application-owned records use UUID primary keys, generated with UUIDv4. API IDs
are UUID strings. Provider-issued voice identifiers, Django's internal tables,
and third-party internal primary keys retain their own formats.

The initial model-creation migrations define UUIDs directly. The temporary
integer-to-UUID conversion migrations and their migration test were removed
after the local database was successfully converted. The existing local data
and UUIDs remain unchanged; no migration reset or database recreation is needed.
This migration history supports fresh databases and the already-converted local
database. It no longer upgrades databases that still contain integer IDs.

Scenes, visuals and video lists use creation timestamps for ordering. Existing
local records retain the ordering timestamps backfilled during conversion; new
records use their actual creation times.
