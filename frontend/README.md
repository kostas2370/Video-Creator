# Viddie frontend

Requires Node.js 22.12 or later. Docker uses Node.js 24 for the build.

```sh
npm ci
npm start
```

Vite serves the app at http://localhost:3000 and proxies API, media, admin, and
documentation requests to Django at http://localhost:8000. React Router handles
client routes, including direct navigation to the video editor.

## Build and checks

```sh
npm run build
npm test
npm run audit
```

Production output goes to `build/`, with hashed assets under `static/`, matching
the Docker nginx configuration. `npm run preview` serves a build locally; use
`npm start` for development with the backend proxy.

The API host is relative by default. Existing `REACT_APP_API_HOST` settings in
the environment or frontend `.env` files remain supported at build time. Only
that setting is copied into the browser bundle; keep provider credentials in
the backend.

Vitest runs the API request regression tests. Tailwind 4 compiles styling locally;
the app does not load Tailwind's development CDN script. Compatibility rules in
`src/index.css` preserve the existing theme and Material Tailwind dialog styling.

Audit the complete dependency tree before release. The frontend audit does not
cover backend packages or the operating-system packages in Docker images.
