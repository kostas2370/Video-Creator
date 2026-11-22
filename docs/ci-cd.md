# Development and production releases

Use feature branches → `develop` → `main`. Open feature PRs against `develop`.
Production releases are PRs from this repository's `develop` branch into `main`.
The branch policy check rejects other sources for `main`, including a fork's
branch named `develop`.

Both branches require passing backend, frontend, branch policy and release-tooling
checks before a PR can merge. Required checks must come from GitHub Actions.
Direct pushes, force pushes and branch deletion are blocked, including for admins.
This owner-operated repository does not require a second person's approval.
Resolve review conversations before merging. Keep release PRs up to date with
`main`; merge `main` back into `develop` through a PR when needed.

## First activation

The workflow files must reach `main` before automatic production deployment can
run. Merge the beta implementation PR into `develop`, then open and merge a release
PR from `develop` to `main` after all required checks pass. Creating branches,
secrets or the workflow files in a feature PR does not deploy an unmerged revision.

After each push to `main`, Django CI and Frontend checks run. The deployment
workflow responds to their completion events and deploys only when both push
checks succeeded for the current `main` commit. Events for older commits are
ignored. Duplicate successful events do not restart an already healthy revision.

## Deployment access

GitHub's `production` environment permits only the `main` branch. It contains:

- Encrypted secret `DEPLOY_SSH_KEY`: a separate Ed25519 deployment key.
- Variable `DEPLOY_HOST`: the VPS hostname or IP.
- Variable `DEPLOY_KNOWN_HOSTS`: the independently verified server host key.

The public key on the VPS uses OpenSSH `restrict` and a forced command pointing
to `/usr/local/sbin/viddie-ci-deploy`. It accepts only `status` or `deploy` followed
by a full lowercase commit SHA. It grants production deployment access, including
Docker builds and database migrations; protect write access to the release branch.
It does not provide an interactive SSH shell, forwarding or a PTY. Host key
checking remains mandatory. The personal administrator key is separate.

R2, YouTube, database and application secrets remain in the private server `.env`.
The workflow does not download those secrets or include them in its source archive.
Never put provider credentials or media files in Git.

## Server layout and release process

`/opt/viddie/backend` retains the private `.env` and persistent working directories.
`VIDDIE_STATE_ROOT=/opt/viddie/backend` keeps these mounts stable across releases.
R2 is the active private media store; local working files support rendering.
PostgreSQL and Redis continue using the existing named volumes.

`/opt/viddie-current` points at the current source checkout. Initially it points at
`/opt/viddie`; subsequent checked releases live under `/opt/viddie-releases/`.
Each staged backend links its `.env` to the persistent private file.

The installed deployment helper:

1. Takes an exclusive server lock and receives a bounded source archive.
2. Rejects paths outside the release, symlinks, secrets, media directories and
   oversized contents. It extracts a fresh directory, so removed source files do
   not survive as they would with an overlay update.
3. Creates empty mount-point directories in the source release and ensures the
   persistent working directories exist. Builds the backend and frontend, then
   verifies a backend container can start with its mounts while the existing app
   is running. A failed startup check leaves the existing services running.
4. Stops the API and scheduler, waits up to ten minutes for queued/active work to
   drain, then stops the workers. Failed draining restarts the old containers.
5. Backs up PostgreSQL and `.env` under `/var/backups/viddie/`. A backup failure
   restarts the existing containers before any schema change is attempted.
6. Applies committed migrations, collects static files, and runs deployment checks.
7. Recreates the API, workers, scheduler, frontend and HTTPS edge. It checks the
   trusted HTTPS API response, active R2 setting and replies from both workers.
8. Updates `/opt/viddie-current` and records the deployed commit only after success.

GitHub serializes deployments and does not cancel one in progress. The server lock
also protects against overlapping manual deployments. A deployment can take the
app offline while jobs finish and migrations run. These checks do not make paid
provider calls or establish real-provider generation quality.

The helper does not force-recreate PostgreSQL or Redis and does not remove volumes.
Database/server-image upgrades need a separate maintenance plan. Backups on the
same VPS are not off-host protection; arrange independent private backups.

## Manual retry and failure recovery

In GitHub Actions, open **Deploy beta**, choose **Run workflow**, and select `main`.
It still requires both successful push checks for that exact current revision.
From your Mac, the equivalent is:

```sh
gh workflow run deploy-beta.yml --ref main
gh run list --workflow deploy-beta.yml --limit 5
```

On the VPS, inspect current services:

```sh
cd /opt/viddie-current/backend
docker compose -f docker-compose.beta.yml ps
docker compose -f docker-compose.beta.yml logs --tail=100 video_creator celery celery-render caddy
```

A build failure leaves the running release untouched. After migrations begin,
the helper never automatically restores a database or runs old code against an
unknown schema. A migration or startup failure leaves the backup and staged
release for inspection, and the workflow fails. The app may remain stopped or
partially started. Use the logged release and backup paths to assess recovery;
restore only with a reviewed data recovery plan. Code rollback requires schema
compatibility and rebuilding the selected prior release's images.

The helper is installed separately from release source. Update its root-owned
installed copy only after reviewing and testing changes to `scripts/deploy_beta.py`.
Monitor release directories, backups and Docker build-cache disk use; automated
retention or pruning is not configured.
