# Frontend dependency audit

`npm run audit` tests the audit policy and scans all dependencies, including development
dependencies. Other high/critical advisories remain blocking. `npm run audit:raw` shows
the original, unfiltered npm report and exits with npm's original status.

## Temporary picomatch exception

- Advisory: https://github.com/advisories/GHSA-fc5q-39xc-vjpf
- Accepted on: 2026-11-18. Expires: **2026-12-02 at 00:00 UTC**.
- Scope: **picomatch 4.0.7**, marked development-only in the committed lockfile,
  and development-only dependencies affected solely by this same advisory.
- Reason: no patched release is published. Earlier releases are also affected;
  the proposed Vite downgrade is breaking and does not remove every dependency path.
- Exposure: this repository uses picomatch through Vite/Vitest tooling. The production
  frontend image serves compiled static assets through nginx; Node and node_modules
  remain in the build stage. This is a temporary risk acceptance, not a patch.

The wrapper logs the exception and original vulnerability totals. It fails for other
high/critical advisories, production dependency paths, a different picomatch version,
expiration, audit execution errors, or unsupported reports. It does not skip all
development dependencies or use `continue-on-error`.

Do not expose the development server publicly or feed untrusted glob patterns into
build/test tooling. When a patched release becomes available, update the lockfile,
verify the raw audit and frontend tests/build, and remove the exception. If no patch
exists by expiry, reassess explicitly rather than extending it automatically.
