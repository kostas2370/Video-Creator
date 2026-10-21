# Creator publishing

Creators can publish the last completed video export to YouTube, TikTok, or Instagram Reels from **Publish** in the editor toolbar. Each platform is connected by its official authorization screen. Viddie never asks for a creator's social password. This first release submits to one account at a time; scheduling and analytics are not included.

## Developer app setup

A platform stays visibly unavailable until its server configuration is supplied. Register applications before testing real account connections. Configure a public HTTPS backend address; account callbacks and Instagram's media fetcher must be reachable from the internet. Do not expose a development server without the normal production deployment configuration.

Set these environment variables on the backend and workers (never in frontend code):

```text
SOCIAL_PUBLIC_BASE_URL=https://api.your-domain.example
SOCIAL_YOUTUBE_CLIENT_ID=
SOCIAL_YOUTUBE_CLIENT_SECRET=
SOCIAL_TIKTOK_CLIENT_ID=
SOCIAL_TIKTOK_CLIENT_SECRET=
SOCIAL_INSTAGRAM_CLIENT_ID=
SOCIAL_INSTAGRAM_CLIENT_SECRET=
SOCIAL_META_API_VERSION=
```

Use the Meta Graph API version chosen in your developer application, such as `v25.0` if that version is supported for your app. There is deliberately no implicit Meta version default. Retain the existing stable `FIELD_ENCRYPTION_KEY` configuration across deployments: account tokens use the same encrypted model fields as existing provider keys. `FRONTEND_URL` must name the public frontend where creators return after connecting.

Register these exact redirect URIs, replacing the example origin with `SOCIAL_PUBLIC_BASE_URL`:

| Platform | Callback |
| --- | --- |
| YouTube | `https://api.your-domain.example/api/publishing/oauth/youtube/callback/` |
| TikTok | `https://api.your-domain.example/api/publishing/oauth/tiktok/callback/` |
| Instagram via Facebook Login | `https://api.your-domain.example/api/publishing/oauth/instagram/callback/` |

### YouTube

Enable YouTube Data API v3 in a Google Cloud project and create a Web application OAuth client. Configure the consent screen, test users, authorized redirects, and the `youtube.upload` and `youtube.readonly` scopes. The latter identifies the channel and checks processing status. Follow Google's verification requirements for external creators.

Creators explicitly choose public, unlisted, or private visibility and whether the content is made for kids. The upload sets the altered/synthetic media disclosure selected by the creator. A processed private or unlisted upload is still reported as successfully completed; this does not mean it is public.

Sources: [OAuth for server applications](https://developers.google.com/youtube/data/guides/auth/server-side-web-apps), [video uploads](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert), [resumable uploads](https://developers.google.com/youtube/data/guides/using_resumable_upload_protocol).

### TikTok

Register an app with Login Kit and Content Posting API. Obtain approval for `user.info.basic` and `video.publish`. Configure the redirect and complete TikTok's review/audit before offering public Direct Post to external creators. Unreviewed clients face account and visibility restrictions; this integration does not override them. Direct Post is intended for creator-facing apps, not internal-only upload utilities.

The composer fetches current creator info, shows the creator's nickname and supported privacy options, leaves visibility unselected, and leaves comments/duet/stitch off by default. Account-disabled interactions cannot be enabled. Submission rechecks current creator constraints; the worker rechecks before starting the transfer. Commercial-content choices change the displayed label and required terms. The creator confirms the preview and music usage terms before submission. AI-generated disclosure is editable and passed to TikTok.

Sources: [Direct Post setup](https://developers.tiktok.com/docs/en/content-posting-api-get-started), [required sharing experience](https://developers.tiktok.com/docs/en/content-sharing-guidelines), [transfer rules](https://developers.tiktok.com/docs/en/content-posting-api-media-transfer-guide), [status](https://developers.tiktok.com/docs/en/content-posting-api-reference-get-video-status).

### Instagram

This release uses **Instagram API with Facebook Login**. Register a Meta Business app and configure Facebook Login for Business and Instagram publishing. Request `pages_show_list`, `instagram_basic`, `instagram_content_publish`, and `pages_read_engagement`; obtain the access level/review required for external creators. The Instagram account must be Business or Creator and linked to a Facebook Page. Each eligible Page/account is listed separately after authorization.

The worker creates a Reel container, waits for processing, then publishes it once. Meta retrieves the immutable export through a signed, job-scoped HTTPS URL valid for 24 hours. This endpoint never accepts arbitrary file paths and never includes an OAuth token. Complete the privacy policy, terms, data-deletion, and business verification requirements shown in your Meta developer dashboard before launching to external creators. Those legal pages and review submissions are deployment responsibilities, not supplied by this feature.

Source: [Meta's official Instagram API collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api).

## Deploying and testing

### Local testing with an HTTPS tunnel

On macOS or Linux, install `cloudflared` and Docker, start the Docker app, then run these commands from the repository root:

```bash
# Enable public access; keep this terminal open.
python3 scripts/local-tunnel.py start

# In another terminal, inspect or disable the managed tunnel.
python3 scripts/local-tunnel.py status
python3 scripts/local-tunnel.py stop
```

Start creates a temporary public HTTPS address for port 3000, updates only `SOCIAL_PUBLIC_BASE_URL` and `FRONTEND_URL` in your ignored `backend/.env`, and reloads the backend and workers. It prints the three callback URLs to register in the developer dashboards. Dashboard callbacks and policy/website URLs must still be updated manually when the hostname changes. Logs and local control files are ignored under `backend/.local-tunnel/`. Stop and Ctrl+C end public access without stopping the Docker app. These controls manage only tunnels launched by this script; stop any older manually launched tunnel from its own terminal first. Stopping the app with `docker compose down` makes the public link unavailable even if the tunnel is still running. Restarting the script creates a new address.

For the Docker development stack, point the tunnel at the frontend on port 3000. Its existing proxy serves `/api/` from the backend, so the browser starts OAuth and receives its callback on the same HTTPS hostname. A backend-only tunnel combined with a localhost frontend will not receive the initiating browser's OAuth cookie at the public callback.

Set both `SOCIAL_PUBLIC_BASE_URL` and `FRONTEND_URL` to that HTTPS origin, register the exact callback URLs with the providers, and recreate the backend and worker containers to reload their environment. Open Viddie through that HTTPS address and sign in there before connecting an account. Tunnel hostnames are temporary: update configuration and provider redirect URLs whenever the hostname changes. Cloudflare Quick Tunnels do not support SSE, so live progress notifications may not work through this test tunnel.

Google's testing consent screen must list the test account and declare `youtube.upload` and `youtube.readonly`; enable YouTube Data API v3. For TikTok, use a named sandbox and its own client credentials, configure Web/Login Kit and Direct Post, and authorize a target test account in the sandbox dashboard. The sandbox form also requires an app icon, category and published legal-page URLs before saving changes. Viddie's public `/terms/` and `/privacy/` pages were approved by the operator for the local testing deployment; review their content and deployment-specific disclosures before a production launch. Platform review and public-posting restrictions still apply.

### Verification

1. Apply migrations with `python manage.py migrate`.
2. Restart backend and Celery workers so the new app, configuration, and tasks are loaded. Ensure the queue is running.
3. Export a video, open **Publish**, connect a developer test account, review the export and posting details, and submit.
4. Verify both the job history and the destination platform. Repeat with a public account only when the developer application has the required approval.
5. Disconnect removes local credentials and cancels queued uploads. Already-started uploads may complete. Creators can also revoke permissions in the destination platform's account settings.

## Reliability and limits

- Creator-owned accounts, videos, and jobs are checked on every authenticated endpoint. OAuth state expires after ten minutes, is consumed once, and is bound to an HttpOnly secure cookie in the initiating browser.
- Tokens are encrypted in the database and omitted from responses. Google and TikTok tokens refresh under an account lock; expired Instagram connections require reconnection.
- A submitted job receives an independent copy of the exported file. A project timestamp check rejects submissions from a stale editor. Later edits and renders cannot change that upload.
- Repeated submissions use an idempotency key. Workers claim jobs once. An uncertain remote result is never automatically uploaded again. Instagram's final publishing step is claimed separately so competing polls cannot publish it twice.
- `NEEDS_CHECK` means inspect the destination before starting another post. Refresh can query a known YouTube/TikTok upload without uploading again. An uncertain Instagram publish is not automatically repeated.
- The first release supports exports up to 4 GB. Instagram enforces the Reel limits documented by Meta's collection (including a 1 GB maximum). It does not transcode incompatible exports automatically.
- Snapshots use `PUBLISHING_SNAPSHOT_ROOT` (default `backend/private-publishing/`), outside public media routes. Mount durable private storage there for backend and workers. Upload snapshots and job history remain until their job/project is deleted; factor their storage into retention planning. Scheduling, public webhooks, custom YouTube thumbnails, and analytics are future work.
- Automated tests mock provider calls. Credentials and platform approval are required for real end-to-end validation; passing tests does not imply an app has been reviewed by a platform.
