# PostgreSQL

Development, production and CI use PostgreSQL. The Compose service runs PostgreSQL
18 with its data in the named `postgres-data` volume, mounted at
`/var/lib/postgresql` as required by the PostgreSQL 18 image. The database has no
host port mapping; API and workers connect on the private Compose network.

Set these values in the ignored `backend/.env` before starting:

```dotenv
POSTGRES_DB=video_creator
POSTGRES_USER=video_creator
POSTGRES_PASSWORD=YOUR_UNIQUE_PASSWORD
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_SSLMODE=prefer
```

Generate a strong password and retain it with the database configuration. Changing
`POSTGRES_PASSWORD` after a volume has been initialized does not update the role's
password; rotate it in PostgreSQL and update the application configuration together.
For a managed or remote production database, use the provider's hostname and TLS
settings, normally `verify-full` with a trusted CA. Use a dedicated application role
with access to its own database. Persistent Django connections are disabled for the
ASGI API.

Development and production inherit the PostgreSQL settings from `base.py`.
CI uses a fresh PostgreSQL service and its own test database.

## Existing SQLite installations

Changing the database setting does not move existing data. Before switching:

1. Keep `SECRET_KEY` and the credential encryption configuration unchanged during
   the database transfer. For the transition to Vault, follow the separate
   [Vault rollout](credential-security.md).
2. Take a consistent SQLite snapshot and check database integrity and foreign keys.
3. Apply the project's migrations to a fresh PostgreSQL database and rehearse the
   transfer. Preserve IDs, encrypted values, relationships, JSON values, timestamps
   and all many-to-many tables. Reset PostgreSQL sequences after importing IDs.
4. Compare every table's row counts and normalized contents, and validate all
   foreign-key constraints. Review any legacy tables outside the current models.
5. Pause API writes, workers and Beat for the final consistent snapshot. Repeat the
   verified transfer, then switch the API and every worker to PostgreSQL together.
6. Check authenticated requests, background jobs and media playback. Keep SQLite
   and its verified snapshot as backups. R2 and local media are unchanged.

Private local snapshots and verification reports belong in the ignored
`backend/.db-backups/` directory with restrictive filesystem permissions. Back up
PostgreSQL independently after cutover. Avoid `docker compose down -v`, which
removes database volumes.

A rollback requires restoring the previous application version and its preserved
SQLite file. After PostgreSQL accepts new writes, reconcile those changes before
rolling back; restoring the old database alone would lose the newer records.
