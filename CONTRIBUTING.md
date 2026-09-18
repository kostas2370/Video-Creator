# Contributing to Viddie

Thanks for taking the time to contribute. This document covers how to get a change
merged: what to run before you open a pull request, the conventions this codebase
follows, and the handful of traps that are specific to this project.

For installation and how to run the stack, see the [README](README.md) — none of that
is repeated here. By participating you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md).

Viddie is licensed under **AGPL-3.0** ([COPYING.txt](COPYING.txt)). Contributions are
accepted under the same licence.

---

## Getting set up

Docker is the fastest path to a working stack, and it is what most contributors should
use:

```shell
cd backend
docker-compose up --build
```

The app comes up on <http://localhost:3000>, with the API, admin and Swagger proxied
through nginx on the same origin. The first boot downloads the SadTalker and GFPGAN
weights (several minutes, once).

Two things that catch people out on a fresh install:

- Open the app on `localhost`, not `127.0.0.1`. They count as different sites, and the
  `SameSite=Strict` refresh cookie will not be sent.
- Logging in through the frontend requires `is_verified` on your user, which normally
  comes from a signup email. With no SMTP configured locally, set it by hand — the
  README has the one-liner.

For frontend work you want hot reload, which Docker does not give you. See
[Working on the frontend](#working-on-the-frontend).

---

## Repository layout

```
backend/
  apps/
    usermanagement/      accounts, auth, JWT, password reset
    videomanagement/     the generation pipeline, scenes, rendering, Twitch
    apikeysmanagement/   per-user provider API keys, stored encrypted
  video_creator/         settings, root urlconf
  requirements/          requirements.txt + constraints.txt
frontend/
  src/api/               axios instances and every API call
  src/pages/             routed pages
  src/components/        shared UI and modals
  src/hooks/             auth, theme, debounce, axios interceptors
```

`backend/apps/videomanagement/utils/SadTalker/` is **vendored third-party code**. It is
excluded from linting in `pyproject.toml` and should not be reformatted, restyled or
tidied up. Patch it only when fixing something that actually breaks.

---

## Before you open a pull request

CI runs on every PR to `main` ([`.github/workflows/django.yml`](.github/workflows/django.yml)).
Run the same four things locally and you will not be surprised:

```shell
# 1. Lint and format (installs the hooks once, then runs on every commit)
pip install pre-commit && pre-commit install
pre-commit run --all-files

# 2. Migrations are committed, so this should find nothing to do
python backend/manage.py makemigrations --check --dry-run

# 3. Django system checks
python backend/manage.py check

# 4. Tests
python backend/manage.py test apps.videomanagement.tests apps.apikeysmanagement.tests
```

### Running the tests

**Name the `tests` packages explicitly.** A bare `manage.py test` — or naming the app
rather than its tests package, as in `manage.py test apps.videomanagement` — walks into
the vendored SadTalker checkout, which ships `test_options.py` files that match the
default discovery pattern and cannot be imported standalone. You get two
`unittest.loader._FailedTest` errors that have nothing to do with your change:

```shell
# Right
python backend/manage.py test apps.videomanagement.tests apps.apikeysmanagement.tests

# Wrong — two spurious SadTalker import errors
python backend/manage.py test
```

Under Docker, run it in the web container:

```shell
docker compose exec video_creator python manage.py test apps.videomanagement.tests apps.apikeysmanagement.tests
```

New behaviour needs a test. The suite stubs every call out to a model provider — no
test reaches the network, and none should start to. `model_bakery` recipes live in each
app's `baker_recipes.py`; prefer extending a recipe over building model instances by
hand.

### Migrations

Generate them with the app labels:

```shell
python backend/manage.py makemigrations usermanagement videomanagement apikeysmanagement
```

A bare `makemigrations` silently skips any app whose `migrations/` package is missing
and reports "No changes detected", which is how a model change reaches CI without its
migration. CI fails the PR if one is missing.

---

## Code style

### Python

`ruff` and `ruff-format` handle formatting and linting through pre-commit. Nothing to
argue about — run the hooks.

### Comments

**This codebase does not use explanatory comments.** Do not write a comment that
explains why the code does what it does, what a block is for, or how something works.
Write the code so it reads without one.

This is a deliberate house style and the most common reason a PR gets change requests
here, so it is worth stating plainly. In practice:

- Name things so the name carries the explanation.
- Test names are full sentences — `test_never_gives_a_twitch_video_an_avatar`,
  `test_one_user_can_never_reach_another_users_keys`. That is where behaviour gets
  described, not in a comment above the assertion.
- Comments that *do* something stay: `# noqa`, `// eslint-disable-next-line`, and
  similar directives are not prose and are not covered by this rule.

If you are stripping comments from code you are touching, **check the line underneath
each one before you delete it**. Comment-removal passes in this repo have twice taken a
line of real code with them — a `filterset_fields` declaration and a boolean coercion —
and both times a test caught it. Run the suite after a cleanup pass.

### Docstrings

Existing docstrings on public functions are fine to leave. Do not add new ones that
restate the signature.

---

## Working on the frontend

Run it outside Docker for hot reload:

```shell
cd frontend && npm install && npm start
```

CRA's dev server proxies `/api` to `localhost:8000` (see `proxy` in `package.json`), so
the browser still sees one origin and the cookies behave.

**The Docker frontend has no source bind mount.** The bundle is compiled into the image
at build time, so a source change is invisible until you rebuild *and* recreate the
container:

```shell
docker compose up -d --build --force-recreate frontend
```

`--build` alone will sometimes restart the existing container on the old image and
leave you debugging a bundle that does not contain your change.

### Calling the API

Every call goes through [`src/api/apiService.js`](frontend/src/api/apiService.js). Add
the endpoint to `API_ENDPOINTS` and export a function next to the others rather than
reaching for axios in a component.

The shared axios instances default to `Content-Type: multipart/form-data`, which suits
the file uploads but stringifies everything else — a boolean arrives at DRF as `"true"`
or `"false"`. If your request carries no file, send JSON explicitly:

```js
{ headers: { "Content-Type": "application/json" } }
```

The `getRequest` / `postRequest` / `patchRequest` helpers swallow errors and resolve
`undefined`. That is fine for a list that can render empty, and wrong for anything the
user needs told about — a failed save that looks like a success is worse than an error
toast. For those, call the instance directly and return a result the caller can branch
on, as `renderVideo` and the API-key calls do.

---

## Commits and pull requests

- Branch off `main`. Branch names are free-form and descriptive (`fix-ci`,
  `queue-generation-and-render`).
- Write commit subjects in the imperative mood, capitalised, no trailing period —
  `Add password reset`, `Serve media from nginx and keep the port in the proxied Host`.
- Keep a commit to one change. A change spanning the API and the UI is one commit,
  since both live in this repository.
- Open the PR against `main` and describe what changed and why. If it changes
  behaviour, say what a reviewer should click to see it.
- CI must be green. A PR with failing tests will not be reviewed.

---

## Secrets and configuration

Never commit a `.env`, an API key, or a model credential. `.env` is gitignored;
[`backend/.env_example`](backend/.env_example) is the template, and every new setting
belongs there with a comment explaining the value — that file is documentation, and the
no-comments rule does not apply to it.

Two settings matter for anyone touching stored credentials:

- `SECRET_KEY` falls back to a development default. Never run a deployment on it.
- `FIELD_ENCRYPTION_KEY` encrypts the per-user provider keys in `apikeysmanagement`. It
  is derived from `SECRET_KEY` when unset, so **changing `SECRET_KEY` on an existing
  database makes every stored API key undecryptable.** Set it explicitly anywhere the
  data needs to survive.

User-supplied API keys are write-only through the API and come back masked. If you add
a field there, keep it that way — there is a test asserting a key never appears in a
response body, and it should stay passing.

---

## Reporting bugs

Open an issue with what you did, what you expected and what happened, plus the relevant
traceback or console output. If it involves generation or rendering, include which
providers and models were configured — most pipeline bugs are provider-specific.

For anything security-sensitive, email the maintainer rather than opening a public
issue:

- [kodamia@cs.ihu.gr](mailto:kodamia@cs.ihu.gr)
- [kostas2372@gmail.com](mailto:kostas2372@gmail.com)
