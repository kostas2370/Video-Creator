# Public homepage and search discovery

Signed-out visitors see the public homepage at `/`. Signed-in users keep the Create
workspace there. Project pages and creation tools continue to require authentication.

Set `VITE_PUBLIC_SITE_URL` to the public HTTPS origin when building the frontend,
for example `https://viddie.example.com`. The Docker build accepts the same build
argument. Vite embeds this value at build time; changing it requires rebuilding the
frontend. Never put credentials in a `VITE_` variable.

The production build creates a sitemap and robots file listing only the homepage,
guide, news, privacy, terms, contact and access-request pages. When no public origin is configured,
the build does not invent a production sitemap hostname. Route metadata supplies
titles, descriptions and canonical links; private routes use `noindex, nofollow`.
These instructions guide search engines and do not replace authorization checks.

Nginx serves `/sitemap.xml` and `/robots.txt` as actual static files rather than
returning the application shell for missing files. Submit the deployed sitemap in
Google Search Console to request discovery. A sitemap does not guarantee indexing
or ranking.

Run `npm test` and `npm run build` from `frontend/` to verify generated files and
public/private routing. Test the signed-out homepage and a signed-in return to Create
after changing the root route.


The homepage includes curated public videos, a keyboard-accessible studio walkthrough,
and an access-request link when the deployment is invite-only. Its light/dark toggle
uses the app’s saved theme. Sample players use click-to-load YouTube embeds; local
posters and screenshots do not contact YouTube before playback. Replacing the
examples requires updating `VideoShowcase.js` and the matching public poster assets.
The access-request page uses the same visual theme and retains inline delivery errors.
