# Production deployment

Use `backend/docker-compose.production.yml` on a single Docker host. It is a
separate stack from local development. PostgreSQL and Redis are private; only the
frontend binds a loopback port for a host-local HTTPS reverse proxy. A real domain
and TLS edge are still required before public launch. Choose a different
`FRONTEND_PORT` when testing alongside development on the same host. This setup does not provision
hosting, DNS, certificates, monitoring, or automated backups.

## Images and private configuration

Copy `backend/.env.production.example` to `backend/.env.production`, restrict access
to the real file, and fill in its values. Use a persistent signing secret, database
password, URL-safe Redis password, and private R2 credentials. For an existing
installation, preserve its signing/encryption keys and verify the database transfer
as described in [PostgreSQL migration](postgresql.md). Do not enable public bucket
access. The Compose project name identifies its volumes; keep it stable.

Set `RELEASE_TAG` to the exact Git commit being built, and retain the previous
images/tag for rollback. Never overwrite an existing release tag with different
code. `BACKEND_IMAGE` and `FRONTEND_IMAGE` may include your registry/repository.
Build from a clean checkout or a CI checkout of that commit. Production backend
images contain the source code and bundled fonts/vendor code; they run as a non-root
user with a read-only filesystem and no source-code bind mounts.

From the repository root:

```sh
docker compose --env-file backend/.env.production -f backend/docker-compose.production.yml build video_creator frontend
```

If building elsewhere, push both tagged images to your registry and pull them on
the deployment host instead. Record the image digests for each release.

## Release and first installation

Start the private dependencies, then run the one-off release. This checks Django's
deployment configuration and committed migrations, applies migrations, and collects
admin/API-documentation static files into a volume served read-only by nginx.

```sh
docker compose --env-file backend/.env.production -f backend/docker-compose.production.yml up -d postgres redis-stack-server
docker compose --env-file backend/.env.production -f backend/docker-compose.production.yml --profile release run --rm release
```

For a new, empty installation, run the optional bootstrap separately to load bundled
voices and initial media. This is explicit because it can call external providers;
review its output and provider settings. Do not replay fixtures on every deployment.

```sh
docker compose --env-file backend/.env.production -f backend/docker-compose.production.yml --profile bootstrap run --rm bootstrap
```

If presenter rendering is needed, provision and verify its model files separately
with the `presenter-models` bootstrap service before accepting presenter jobs. Model
downloads are not part of worker startup. These models and local processing caches
need disk space even though published media lives in private R2.

Only after the release and any required first-install setup succeed, start services:

```sh
docker compose --env-file backend/.env.production -f backend/docker-compose.production.yml up -d --wait --wait-timeout 180 video_creator celery celery-render celery-beat frontend
```

The API starts directly; it does not generate migrations, replay fixtures, download
catalog media, or contact provider setup APIs on a restart. Workers use prefork with
explicit concurrency; start conservatively and measure render memory/CPU usage.
There must be exactly one Beat scheduler per deployment.

## Readiness and HTTPS

`/api/health/live/` reports that Django can respond. `/api/health/ready/` checks the
database and authenticated Redis connection without returning private connection
details. Both are unauthenticated and non-cacheable. The frontend has its own
`/healthz`. Workers have targeted Celery ping checks; Beat checks its scheduler PID.
An unhealthy status is reported to Docker; restart policies restart exited processes,
not a live process merely marked unhealthy. Alerting/automatic recovery from hangs
requires a supervisor or hosting platform.

Terminate HTTPS at a host-local edge, forwarding to the configured loopback frontend
port. Overwrite `X-Forwarded-Proto` at that edge and preserve the public Host header.
Do not expose the private API directly or trust client-supplied proxy headers. Set
`ALLOWED_HOSTS` and `FRONTEND_URL` to the actual domain before launch. Verify login,
secure cookies, password-reset email, private R2 images and video ranges through the
HTTPS edge. Run Django deployment checks using the final environment; review any
remaining warnings, including domain-specific HSTS choices.

## Updates and rollback

1. Build/pull the new tagged images before the maintenance window. Keep the current
   images and a record of their tags/digests. Confirm a restorable PostgreSQL backup
   and secure copies of the encryption/signing keys before schema changes.
2. Pause new requests/jobs at the edge, stop Beat, and drain active workers. Workers
   have a two-hour shutdown grace period for long jobs. Stop the API and workers
   before applying migrations; do not let old code write during a schema change.
3. Change `RELEASE_TAG`, run the one-off release, then start the new services with
   `--wait`. Keep traffic paused if the release or readiness checks fail.
4. Check authenticated requests, media playback and a small generation/export, then
   reopen traffic. Test provider-specific features in staging before public rollout.

For a backward-compatible schema, pause/drain again, select the previous image tag,
restore its collected static files using a one-off `release` container with command
`python manage.py collectstatic --noinput`, and recreate the services with `--wait`.
Do not automatically reverse database migrations. A breaking schema change requires
a reviewed data rollback/forward-fix plan; restoring a database backup can discard
new writes. Image rollback alone cannot undo those changes.

Redis uses authenticated AOF persistence in its own volume. This reduces queue loss
on recreation but does not make jobs exactly-once or replace a backup strategy.
PostgreSQL, Redis, static files, model weights, and processing caches have separate
named volumes. R2 is the media store; media is streamed from R2 rather than served
from those processing caches. Never remove volumes during a normal deployment.
Do not automatically delete existing cache/media files until a separately verified
retention policy exists.

References: [Docker Compose in production](https://docs.docker.com/compose/how-tos/production/),
[Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/),
[Redis persistence](https://redis.io/docs/latest/management/persistence/).
