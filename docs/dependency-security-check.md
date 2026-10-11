# Security check — 11 October 2026

## Result

The updated frontend, API, and workers are running locally. All six Compose
services are running. The frontend has zero npm audit findings. New backend
builds retain one unpatched BasicSR advisory, explicitly excepted from CI auditing
because the current deployment does not use its SLURM path. This is not a
public-production sign-off: the active stack uses development settings.

## Security changes

- Replaced Create React App with Vite and Vitest, updated vulnerable frontend
  dependencies, removed unused packages, and removed the Tailwind development CDN.
- Updated python-dotenv, setuptools, and imageio-ffmpeg.
- Upgraded CPU PyTorch to 2.14.1 and torchvision to 0.29.1 in Docker, CI, constraints,
  and manual setup instructions. Removed unused torchaudio.
- Removed unused Djoser and its vulnerable social-auth dependency chain. Its
  `/api/auth/` routes are removed; the existing custom login, registration, email
  verification, password reset, and refresh routes remain.
- Fixed a critical development file-serving issue. An empty media URL prefix
  previously served the backend root, including `/.env`, the database, and source.
  Development serving is now restricted to `/media/` and the media directory.
  Verification discarded private response bodies without displaying or saving them.
- Added backend CI auditing and regression tests for removed auth routes and
  private file protection.

## Audit exception

The audit reports BasicSR 1.4.2 under PYSEC-2026-1215 (CVE-2024-27763), a
command-injection issue in its SLURM cluster helper. Builds install the upstream
dependency without a custom source patch.

CI excludes only PYSEC-2026-1215 as an accepted exception for the current deployment,
which does not use SLURM. Every other advisory remains blocking. This exception
is not a vulnerability fix; reassess it before enabling SLURM. Previously built
local images still contain the patch until rebuilt.

## Validation

- Fresh backend image: all **829 tests passed** during the initial review.
  Django system checks passed, and `pip check` found no dependency conflicts.
- Real SadTalker/PIRender CPU avatar render passed with the fresh image and existing
  checkpoints. Output: H.264 256×256 video, AAC audio, 0.6-second duration.
- Frontend: eight API and background-job regression tests, production build,
  Docker build, and npm audit passed; zero findings across production and development dependencies.
- Live API: `/.env`, `/db.sqlite3`, `/video_creator/settings/base.py`, and removed
  `/api/auth/jwt/create/` return 404. Unauthenticated `/api/videos/` returns 401.
  Existing avatar media returns 200 through both API and frontend entry points.
- The frontend's unknown paths return its HTML app shell; they do not serve backend
  files. Protected API requests through the frontend still return 401.
- Updated API, workers, and frontend images were applied locally after confirming
  the worker had no active jobs.

## Remaining release requirements and limits

- Run with `ENV=prod`, explicit allowed hosts, production database configuration,
  and secure credentials. The current local deployment remains in development mode.
- The production Django deployment check reports missing HTTPS redirect and HSTS.
  Configure and verify these against the actual TLS proxy before public release.
- Review public port exposure, including Redis, and trusted proxy configuration.
- If this instance was reachable by other people while private files were exposed,
  treat credentials in its environment file as potentially exposed and rotate them.
  Preserve the existing field-encryption key when rotating Django's signing key so
  stored provider credentials remain decryptable.
- Paid provider calls and a full user registration-to-generation journey were not
  exercised. The generation tests mock external providers.
- Operating-system packages in the Docker images were not vulnerability-scanned.
