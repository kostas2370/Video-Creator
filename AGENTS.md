# Project rules for coding agents

## Project context

Viddie is a self-hosted video creation app with a Django/Celery backend in
`backend/` and a React/Vite frontend in `frontend/`. Read `CONTRIBUTING.md`
before changing code. Consult `docs/ARCHITECTURE.md` and the relevant guides in
`docs/` when changing generation, rendering, storage, or publishing.

## Working approach

- Understand the existing implementation and nearby tests before editing.
- Make the smallest complete change that solves the requested problem. Fix the
  underlying cause; avoid unrelated cleanup and speculative abstractions.
- Follow existing patterns and reuse shared utilities before adding new ones.
- Preserve unrelated work in the checkout. Do not revert, overwrite, or delete
  changes you did not make.
- Proceed with reasonable assumptions for routine, reversible decisions. Ask
  when missing information materially changes the result or an action risks
  irreversible data loss.
- Keep dependencies minimal. Explain any dependency addition and update the
  appropriate dependency and lock files together.

## Code quality

- Prefer clear names, small cohesive functions, and explicit error handling.
- Follow the repository's no-explanatory-comments convention. Keep tool directives;
  do not add docstrings that merely repeat function signatures.
- Keep frontend API calls in `frontend/src/api/apiService.js`. Send JSON explicitly
  for requests without files, and ensure failed saves cannot appear successful.
- Keep expensive generation and rendering work in the existing background-job
  architecture. Preserve retry safety and reuse of completed media.
- Do not reformat or tidy `backend/vendor/`. Change vendored code only for a
  necessary, focused fix.
- Keep user-facing controls accessible, responsive, and consistent with the
  existing interface. Provide useful loading, empty, and error states.

## Security and data

- Never commit or expose secrets, `.env` contents, provider keys, or private user
  data. Add new configuration to `backend/.env_example` without real credentials.
- Preserve authentication, CSRF protection, ownership checks, private media access,
  and encryption of provider credentials. Keep API keys write-only and masked.
- Validate untrusted input at system boundaries. Keep sensitive provider responses
  and internal tracebacks out of user-facing errors.
- Include migrations for model changes. Do not rotate secrets, reset databases,
  or remove persistent media as part of an ordinary code fix.
- Mock paid providers and external publishing in tests; do not incur charges or
  publish real content merely to verify a change.

## Verification

- Add or update meaningful tests for changed behavior, including relevant failure
  and permission cases. Documentation-only edits do not require application tests.
- Run focused checks while working, then the applicable checks from
  `CONTRIBUTING.md` before handing off. Report anything you could not run.
- Backend checks from the repository root:
  - `pre-commit run --all-files`
  - `python backend/manage.py makemigrations --check --dry-run`
  - `python backend/manage.py check`
  - `python backend/manage.py test apps.videomanagement apps.apikeysmanagement apps.usermanagement`
- Name Django apps or test modules explicitly; bare test discovery enters vendored
  third-party tests. Generate migrations with explicit app labels.
- Frontend checks from `frontend/`: `npm test` and `npm run build`.
- Inspect visible UI changes in the browser when available. Verify the relevant
  interaction and mobile layout, not just compilation.
- Review the final diff for accidental edits, missing migrations, and secrets.
  Never claim a check passed unless it actually ran successfully.

## Communication and handoff

- Use concise, plain language and give brief progress updates during longer work.
- Explain what changed, why it matters, what was verified, and any remaining
  limitations. Link to relevant files when useful.
- Update the relevant documentation when behavior, configuration, or setup changes.
- Complete the requested work through verification; do not stop at a plan when
  implementation is requested.
