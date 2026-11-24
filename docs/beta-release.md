# First beta deployment

The first hosted beta uses personal provider keys, CPU rendering, and invited
accounts. Production defaults disable SadTalker and shared provider credentials,
including for existing accounts that previously selected service keys. Missing
personal keys never fall back to operator keys. Development keeps its existing
optional features. Deployment environment variables control these policies; the
frontend reads the public feature flags from the backend at runtime.

## Hosting target

Start with an x86 Linux VPS with 4 vCPUs, 8 GB RAM, and at least 75 GB SSD storage.
This is a starting configuration for a small beta, not a measured capacity promise.
Run one render worker and one general worker. Production defaults to two encoding
threads; `RENDER_THREADS` can set 1–8. Watch free disk space, memory, queue wait,
and render failures before increasing concurrency. The beta build excludes
SadTalker dependencies when `SADTALKER_ENABLED=false`; development Docker builds
include them by default. The unused `g4f` package is no longer installed.

On 21 November 2026, [OVH's Ireland listing](https://www.ovhcloud.com/en-ie/vps/)
advertised VPS-2 with 4 vCores, 8 GB RAM and 75 GB NVMe from €7.21/month excluding
VAT. Verify billing country, availability, commitment, renewal price, and the final
checkout total before ordering. The server budget is approximately €10/month;
domain registration, email delivery, and independent backup storage are separate.
A Contabo Cloud VPS 6 has since been purchased for a one-month initial term.
Verify its actual renewal price and billing terms in the customer panel. Domain
registration is complete at Porkbun: `viddiecreator.com`. It points to the VPS
and is the canonical HTTPS hostname. `www.viddiecreator.com` and the original
`84-54-23-130.sslip.io` address redirect to it, preserving request paths.

## Configure a new host

Use a supported x86 Ubuntu LTS installation with Docker Engine and Compose. Permit
SSH only as needed, and public TCP ports 80/443. Database,
Redis, frontend, and API ports are not published by the beta Compose file.

Caddy serves HTTPS over HTTP/1.1 and HTTP/2. HTTP/3 is disabled because Chrome
received response headers but stalled downloading API bodies over that transport
on the initial VPS deployment. `Alt-Svc: clear` clears cached HTTP/3 advertisements.
After switching to HTTP/2, Chrome loaded recent projects in 248 ms and displayed
the project cards. This measurement is one observed request, not a capacity test.

Choose a domain or subdomain, point its DNS at the server, and check out the reviewed
release revision. Keep this checkout private to the server operator. Run the
following from `backend/` on that host:

```sh
cp .env_example .env
chmod 600 .env
mkdir -p media staticfiles private-publishing private-clips private-render-cache
```

Set these values in `.env`:

- `BETA_DOMAIN`: the canonical hostname only, without a scheme or path.
- `BETA_ALIASES`: optional space-separated HTTPS hostnames that redirect to the
  canonical host. Point their DNS at the same server first; leave blank for none.
- `SECRET_KEY`: a persistent random secret of at least 50 characters.
- [Vault Transit](credential-security.md) for stored provider credentials and
  publishing tokens. Convert stored credentials before upgrading an existing deployment.
- `POSTGRES_PASSWORD`: a unique random database password.
- `R2_STORAGE_ENABLED=true`: use private R2 for active media storage and delivery.
- `R2_ACCOUNT_ID`, `R2_BUCKET_NAME`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, and
  optional `R2_JURISDICTION`: the existing private bucket connection. Keep these
  credentials in the server's private environment only. Verify existing media
  objects before enabling R2; see [R2 storage](r2-storage.md).
- `SADTALKER_ENABLED=false`: hide presenters and prevent their use by the API and
  render workers. Set `true` only on a host with the optional dependencies and
  model weights installed. The beta Compose build reads this value too; enabling
  it requires a backend image rebuild and running `setup_checkpoints` once.
- `SERVICE_API_KEYS_ENABLED=false`: require personal account provider keys. Set
  `true` to allow accounts to opt into configured operator credentials.
- `INVITE_ONLY=true`: restrict new registrations to `BETA_SIGNUP_EMAILS`. Set
  `false` to allow public registration, subject to `USER_LIMIT` and rate limits.
- `BETA_SIGNUP_EMAILS`: comma-separated invited email addresses. Empty closes signup;
  existing accounts can still log in. `USER_LIMIT` defaults to ten accounts.
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`: working SMTP
  credentials for verification and password-reset emails. The current SMTP setup
  uses STARTTLS, typically on port 587.

Generate each secret locally on the server and save it directly into the protected
environment file. Do not paste secrets into chat, commit them, or regenerate them
on each deployment. Operator provider keys can remain blank. Each tester adds
their own keys through **API keys & providers**.

For CI/CD, supply these as runtime deployment variables or keep them in the host's
private `.env`; do not bake secrets into images or commit `.env`. Apply changes by
recreating the API, both workers, and Beat together. A restart alone does not load
changed Compose environment values. Reload the browser after deployment to fetch
the updated flags; no frontend rebuild is needed for these switches.

When changing SadTalker from disabled to enabled, use literal `true`/`false` in
the beta environment and rebuild the backend before recreating these services:

```sh
docker compose -f docker-compose.beta.yml build video_creator
docker compose -f docker-compose.beta.yml run --rm video_creator python manage.py setup_checkpoints
```

```sh
docker compose -f docker-compose.beta.yml up -d --force-recreate video_creator celery celery-render celery-beat
```

The beta Compose file forces production mode and the HTTPS origin from
`BETA_DOMAIN`. It uses a read-only source checkout with separate writable media,
private storage, and collected-static directories. Its network reserves
`172.30.230.0/24`, with automatic addresses limited to `172.30.230.128/25`
so Caddy's `172.30.230.2` cannot be assigned to another container. If this conflicts
with another host network, change that subnet
and Caddy's fixed address together with `deploy/proxy-trust.conf`.

```sh
docker compose -f docker-compose.beta.yml config --quiet
docker compose -f docker-compose.beta.yml build
docker compose -f docker-compose.beta.yml up -d postgres redis-stack-server
docker compose -f docker-compose.beta.yml run --rm video_creator python manage.py migrate
docker compose -f docker-compose.beta.yml run --rm video_creator python manage.py loaddata fixtures/fixtures.json
docker compose -f docker-compose.beta.yml run --rm video_creator python manage.py collectstatic --noinput
docker compose -f docker-compose.beta.yml run --rm video_creator python manage.py check --deploy
docker compose -f docker-compose.beta.yml up -d
```

Load the voice fixtures only for a fresh installation. For later releases, back up
first, apply committed migrations and collect static assets, then recreate the
app, both workers, Beat, and frontend together. Do not generate migrations on the
production host. The beta configuration bypasses the development startup script
and does not download sample media, music catalogs, or presenter weights.

Populate the shared asset catalogue records explicitly after the first migration.
For an existing R2 installation, import the shared catalogue metadata from its
trusted database, keeping the original relative file names, approvals, attribution
and licenses. The media already in R2 does not need transferring to the VPS. Do
not copy account records, credentials or private project metadata as part of a
shared catalogue import. New VPS media must be published and verified before
enabling R2, so existing project output continues to work.

For a fresh catalogue without existing R2 objects, use:

```sh
docker compose -f docker-compose.beta.yml run --rm video_creator python manage.py download_icons
docker compose -f docker-compose.beta.yml run --rm video_creator python manage.py setup_music_catalog --best-effort
```

These commands are safe to rerun and retain existing catalogue records. Check the
reported download and approval counts: successful music metadata setup alone does
not make tracks playable. The VPS may be unable to download YouTube audio. Reuse
verified existing R2 objects and import their metadata when available.
`MUSIC_CATALOG_AUTO_SETUP` controls the development startup
scripts; the beta stack uses the explicit setup step above.

Caddy obtains and renews HTTPS certificates. Only Caddy's fixed internal address is
trusted for the original client IP. nginx overwrites forwarding headers before
passing them to Django. Keep nginx/API private; do not reuse the proxy-trust snippet
on an unrelated public deployment. Collected Django admin and Swagger assets are
served by nginx, with the development backend fallback retained.

## Automatic releases

Use the [CI/CD guide](ci-cd.md) for the protected feature → develop → main flow,
restricted deployment access, persistent state paths and recovery procedure.
Production deployment activates once the workflow files are merged through
`develop` into `main`; it does not deploy feature PRs.

## Before inviting testers

- Verify HTTPS and HTTP-to-HTTPS redirection at the real domain.
- Register an invited account, receive and follow its verification email, log in,
  reset its password, and log out. An uninvited address must be rejected.
- Confirm the service-key switch and presenter controls are absent. An API request
  enabling service keys or selecting a presenter must also fail.
- Confirm another account cannot access the first account's project or private
  media, including range requests. A deliberately created public share is separate.
- With the operator present, use one account's own provider key for a short real
  storyboard, image, narration, editing, and export journey. This incurs that
  account's provider charges. Automated preparation uses mocks and fake keys only.
- Check that generation and rendering reach their separate queues and that the
  app recovers after a worker restart. Review memory and disk use during export.
- Review the privacy/terms text for the actual host, email provider, media storage,
  retention, backup arrangements, and enabled social integrations before launch.

The deployment check intentionally does not enable HSTS for every subdomain or
browser preload. These require domain-wide decisions; retain the existing
one-year HSTS policy on this app's HTTPS host.

## Backups and restore

Back up PostgreSQL, `media/`, `private-publishing/`, `private-clips/`, and the
protected `.env` containing the encryption key. Render caches and collected static
files can be rebuilt. A provider's daily server snapshot is useful but does not
replace an independent copy. Encrypt backups before off-host transfer, restrict
access, and set retention appropriate to the beta's data policy.

For a consistent local backup, first let active jobs finish and temporarily stop
the API, both workers, and Beat. Leave PostgreSQL running. Use `umask 077`, create a
new private backup directory outside the served checkout, then save:

```sh
docker compose -f docker-compose.beta.yml exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > /path/to/private-backup/database.dump
tar -czf /path/to/private-backup/files.tar.gz .env media private-publishing private-clips
```

Restart the stopped app services after backup. Test restore into a separate empty
database and temporary media directory, never over the running database. Use
`pg_restore --exit-on-error`, the same encryption key, and the matching application
revision; verify account authentication, decrypted personal keys, projects, and
media content. Schedule and verify off-host backups once the server and backup
destination have been chosen.

Preparation included an isolated PostgreSQL 18 dump/restore rehearsal with a fake
account, encrypted fake provider key, private project and test image. This does not
establish that a future server's backup schedule or off-host storage works.

## Image verification during preparation

The lean backend passed 2,105 tests on the local ARM64 image, with the optional
SadTalker test excluded and one existing skip. Production is built separately on
the x86 server. The local image reported 469,936,323 bytes versus 941,800,282 bytes
for the prior development image (about 50% smaller). These are local Docker image
size measurements, not a benchmark of rendering speed.

The patched image uses the official Node.js 24.22.3 binary at the path used by
pytubefix. Its bundled npm tools are removed because the app only calls Node.
The Python nodejs-wheel-binaries package metadata still describes its original
distribution; check the actual interpreter version when auditing this image.
The frontend uses nginx 1.30.7.

Docker Scout's ARM64 and deployed x86 image scans on 21 November 2026 each
reported zero critical and twenty high findings after these updates. Nineteen are Debian base-library findings
marked as having no fixed package by the scanner; they are not waived or proven
unreachable by this preparation. One setuptools 70.3.0 finding points only at
pip's vendored `bom.cdx.json`; the installed setuptools is 84.2.1. This metadata
finding needs separate assessment. Keep signup closed, use only the operator
account for the preview, and review remaining findings before inviting testers.
