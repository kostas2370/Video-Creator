# Viddie - AI-Powered Video Creation

## Short Description
Viddie is an AI-powered platform for automated video creation, utilizing advanced machine learning models. It streamlines video production by combining OpenAI GPT models for script generation, API text-to-speech (OpenAI, ElevenLabs or 60dB) for speech synthesis, OpenAI `gpt-image` models for image generation, and SadTalker for avatar animation. This allows users to generate high-quality videos with minimal manual effort.

![The generation form](docs/screenshots/generate.png)

## Frontend

The React app lives in [`frontend/`](frontend/) and is part of this repository, so a
change that spans the API and the UI is one commit and one review. It was previously
a [separate repo](https://github.com/kostas2370/video_creator_frontend), kept for
history.

Docker serves it through nginx on the same origin as the API, which is what keeps the
auth cookies working: they are `SameSite=Strict`, so a frontend on a different host or
port never receives the refresh token and every reload logs the user out.

## Sample Videos

- [Demo Video 1](https://www.youtube.com/watch?v=PvrX_jq4fv4)
- [Demo Video 2](https://www.youtube.com/watch?v=bNZvK68O-Rk)

---

## Configuration

Both installs read the same `.env` in `backend/` (see `backend/.env_example`).
Three keys are worth setting before you start:

- `OPEN_API_KEY` — used for scripts, images and voices
- `SEARCH_ENGINE_ID`
- `API_KEY`

These are the *service* keys — the ones the server spends on behalf of everyone.
Users can instead supply their own from the app, without touching `.env`; see
[API keys](#api-keys). The service keys are still worth setting, because they are
what new accounts use by default and what the `setup_elevenlabs` and `setup_60db`
commands read.

*To find your Google search engine ID and API key, refer to this *[***YouTube Guide***](https://www.youtube.com/watch?v=D4tWHX2nCzQ\&t=127s)*.*

Every value is optional apart from those, and blank is treated the same as unset.
The ones worth knowing about:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DEFAULT_GPT_MODEL` | `gpt-5.4-mini` | Script generation model |
| `MAX_TOKENS` | `3900` | Visible reply budget |
| `REASONING_TOKEN_ALLOWANCE` | `8000` | Extra budget for gpt-5/o-series thinking tokens, which bill against the same cap as the reply |
| `IMAGE_MODEL` | `gpt-image-2` | Image generation model (DALL-E is retired) |
| `IMAGE_QUALITY` / `IMAGE_SIZE` | `high` / `1792x1024` | Validated per model — change them together with `IMAGE_MODEL` |
| `SUBTITLE_FONT` | `DejaVu-Sans` | ImageMagick font name for subtitles |

---

## How to Run the Project

Docker is the fastest way in and the one most people should use: it brings up the
API, the worker, the database and the frontend together, patches the ImageMagick
policy, ships a subtitle font and downloads the model weights for you. Install it
by hand if you would rather run the services yourself.

### Docker Installation

1. Create the `.env` file as described under [Configuration](#configuration).
2. Navigate to the backend folder and run:
   ```shell
   docker-compose up --build
   ```

This brings up the whole stack, frontend included:

| | |
| --- | --- |
| App | <http://localhost:3000> |
| API | <http://localhost:3000/api/> (also on `:8000` directly) |
| Admin | <http://localhost:3000/admin/> |
| Swagger | <http://localhost:3000/swagger/> |

nginx serves the built app and proxies `/api`, `/admin`, `/swagger` and `/redoc` to
Django, so everything is one origin.

Rendered videos, scene images and narration audio under `/media` are served by nginx
straight off the bind mount rather than through Django. Django's development static
view does not implement range requests, so a browser could not seek in a rendered
video and had to download the whole file before playing it.

The frontend image is a multi-stage build — node compiles the bundle and only the
static output plus nginx is shipped, so it is around 100MB rather than the couple of
GB an installed `node_modules` takes.

To work on the frontend with hot reload, run it outside Docker instead:

```shell
cd frontend && npm install && npm start
```

CRA's dev server proxies `/api` to `localhost:8000` (see `proxy` in `package.json`),
so the browser still sees a single origin and the cookies behave the same way.

Everything above is handled inside the image: the ImageMagick policy is patched, a
subtitle font is present, and the web container runs migrations and loads fixtures on
start. The stack builds natively on both x86\_64 and arm64 (Apple Silicon).

The model weights are downloaded for you: the celery worker runs `setup_checkpoints` before it starts consuming tasks, since it is the service that runs SadTalker. They land in `checkpoints/` and `gfpgan/weights/` on the host through the `.:/app` bind mount, so the first boot pays for the download once and every rebuild after that reuses it. Expect the worker to take several minutes to come up the first time.

They are deliberately **not** baked into the image — that would add several GB to it, and they are not needed at build time.


---

### Manual Installation

#### Prerequisites

- Recommended Python version: 3.9 - 3.11
- Install the following dependencies:
  1. FFmpeg (Required for video rendering) - [Installation Guide](https://phoenixnap.com/kb/ffmpeg-windows)
  2. ImageMagick (Required for subtitles) - [Download](https://imagemagick.org/script/download.php#windows)

     On Linux, the packaged `policy.xml` blocks the `@file` reads that moviepy uses to
     draw text, so every subtitle fails with *"operation not allowed by the security
     policy"*. Delete this line from `/etc/ImageMagick-*/policy.xml`:

     ```xml
     <policy domain="path" rights="none" pattern="@*"/>
     ```

     Subtitles are drawn with the font named by `SUBTITLE_FONT` (default
     `DejaVu-Sans`). Run `convert -list font` to see what your install offers — on
     macOS and Windows `Arial` works, in debian-slim only the DejaVu family exists.

#### Installation Steps

1. Navigate to the viddie folder and install dependencies:

   ```shell
   PIP_CONSTRAINT=requirements/constraints.txt pip install -r requirements/requirements.txt
   ```

   The constraints file holds torch to the CPU build. Without it, several of the
   SadTalker dependencies pull a CUDA build in and add roughly 2.5GB of `nvidia-*`
   packages that nothing here can use.

2. Download the SadTalker and GFPGAN model weights:

   ```shell
   python manage.py setup_checkpoints
   ```

   This fills `checkpoints/` and `gfpgan/weights/` and skips anything already there, so it is safe to re-run if a download drops out. The files come from [Google Drive - Checkpoints](https://drive.google.com/drive/u/1/folders/1Fp4sjMi6U3bQaKmQQe04qeXzk7quu0Od) if you would rather fetch them by hand — note that the `gfpgan` subfolder belongs at `gfpgan/weights/`, not inside `checkpoints/`.

3. Create the `.env` file described under [Configuration](#configuration).

4. Run the following commands to set up the database and start the server:

   ```shell
   py manage.py migrate
   py manage.py loaddata fixtures/fixtures.json
   py manage.py setup_media
   py manage.py createsuperuser
   py manage.py runserver
   ```

   Migrations are committed to the repo, so `migrate` is all you need. If you change a
   model, generate them with the app labels — `makemigrations usermanagement
   videomanagement` — since a bare `makemigrations` silently skips any app whose
   `migrations/` package is missing and reports "No changes detected".

   `fixtures.json` carries the voice catalogue and nothing else — no accounts — so
   `createsuperuser` above is what gives you a login. See
   [Creating a superuser](#creating-a-superuser) if you would rather not answer its
   prompts.

   Voices are all API-backed — OpenAI, ElevenLabs or 60dB. The fixtures load the six
   OpenAI voices, so `OPEN_API_KEY` alone is enough to render speech. Local on-device
   synthesis (coqui/TTS) has been removed: it pinned the project to a dependency tree
   that no longer resolves on Python 3.9, and it was the single largest contributor to
   the image size.

5. (Optional) To enable ElevenLabs voices, add your `XI_API_KEY` in the `.env` file and run:

   ```shell
   py manage.py setup_elevenlabs
   ```

6. (Optional) To enable 60dB voices, add your `SIXTYDB_API_KEY` in the `.env` file and run:

   ```shell
   py manage.py setup_60db
   ```

   This imports your 60dB voices into the database. Once imported, a 60dB voice can be
   selected for a video just like any other voice — synthesis is routed automatically.

7. In a second terminal, start the frontend:

   ```shell
   cd frontend && npm install && npm start
   ```

   It opens on <http://localhost:3000> and proxies `/api` to the Django server on
   `:8000`, so the browser sees one origin and the auth cookies work. Open the app on
   `localhost`, not `127.0.0.1` — they count as different sites, and the
   `SameSite=Strict` refresh cookie would not be sent.

---

## Admin Panel

- URL: [http://localhost:3000/admin/](http://localhost:3000/admin/) under Docker, or
  [http://localhost:8000/admin/](http://localhost:8000/admin/) against `runserver`.
- The fixtures ship no accounts, so create your own — see below.

![The Django admin](docs/screenshots/admin.png)

## Creating a superuser

`createsuperuser` prompts for a username, email and password:

```shell
python manage.py createsuperuser
```

That is enough for the admin, but **not** to sign in through the app: the API login
also requires `is_verified`, which is normally set by following a link emailed at
signup and so never gets set with no SMTP configured locally. This one-liner creates
the account and verifies it in a single step:

```shell
python manage.py shell -c "
from apps.usermanagement.models import User
User.objects.create_superuser(
    username='admin',
    email='admin@example.com',
    password='change-me',
    is_verified=True,
)
"
```

Under Docker, run it in the web container:

```shell
docker compose exec video_creator python manage.py shell -c "..."
```

To verify an account you already made, rather than creating one:

```shell
python manage.py shell -c "from apps.usermanagement.models import User; User.objects.update(is_verified=True)"
```

## API keys

Keys do not have to live in `.env`. Signed in, choose **Providers** in the main menu,
or **API keys and providers** in the account menu, to manage your own from the
browser (<http://localhost:3000/api-keys/>).

The page has two tabs: **Built-in API keys** for the supported services, and
**Custom voice providers** for your own text-to-speech service. Switching tabs keeps
unsaved changes in place.

![Built-in API keys with separate provider tabs](docs/screenshots/api-keys.png)

The page has one switch at the top that decides whose keys generation spends:

| Switch | What gets used |
| --- | --- |
| **Use my own keys** — off (default) | The service keys from `.env`. Anything you saved is kept but unused. |
| **Use my own keys** — on | Your saved provider keys and your custom voice providers. |

The **Built-in API keys** tab lists the supported services: OpenAI, Anthropic, Google Gemini,
ElevenLabs, 60dB, Stable Diffusion, Midjourney, Google Custom Search (key and engine
id), and the Twitch client id and secret. Enter the keys you want to change, then
click **Save**. Only changed fields are sent, so updating one never disturbs the
rest. **Clear** marks a single key for removal on save; **Remove all my keys** removes
all built-in provider keys after confirmation. Custom providers are managed separately
in their own tab.

![Confirming removal of built-in provider keys](docs/screenshots/modal-clear-keys.png)

Two things to know before switching over:

- **There is no fallback.** With your own keys selected, a provider you left blank has
  no key at all — it does not quietly fall back to the service key, and the steps that
  need it will fail. Fill in every provider you actually use.
- **Keys are write-only.** They are stored encrypted and never sent back to the
  browser; a saved key only ever shows masked, as `sk-••••••••ijkl`. That also means
  there is no way to read one back out of the UI — if you lose the original, replace it.

### Custom voice providers

Open the **Custom voice providers** tab to connect your own text-to-speech API.
Each card shows its authentication method and whether a voices URL is configured.
Custom voices are available only while **Use my own keys** is on; the tab offers a
shortcut to switch if service keys are selected.

![Custom voice providers in their own tab](docs/screenshots/custom-providers.png)

Choose **Add provider** and fill in the three sections:

1. **Connection:** give the provider a unique name and enter its speech endpoint URL.
2. **Authentication:** choose a bearer token, custom header, basic authentication
   (`username:password`), or no authentication. Enter the header name when using a
   custom header.
3. **Voices:** optionally enter a voices URL. Without one, the provider can be saved,
   but it will not import voices into the generation picker.

![Adding a custom voice provider](docs/screenshots/custom-provider-form.png)

Under **Advanced: request field names**, the defaults are `text` and `voice_id`.
Change them if your service expects different JSON field names. The speech endpoint
receives a POST with those two fields and should return audio bytes.

The voices URL must be accessible without authentication. It can return a JSON list,
or an object containing that list under `voices` or `data`. Each voice needs `id` and
`name`; `preview_url` is optional. For example:

```json
{
  "voices": [
    { "id": "narrator", "name": "Narrator" }
  ]
}
```

Adding a provider queues its initial voice import. Failed imports keep previously
imported voices; successful refreshes update their names and preview URLs and remove
voices no longer returned by the service. Use **Refresh voices** after editing
its connection or when the service's voice list changes, then reload the generation
page after the background import finishes. “Voice import queued” means the request was
accepted; it does not confirm that the import has completed.

**Edit** opens the form inside the card. Leave the credential field blank to keep the
saved credential, type a replacement to change it, or select **Clear saved credential
on save** to remove it. **Show** reveals only the replacement you typed. Provider
names stay fixed after creation; add a new provider to use a different name.

**Delete** asks for confirmation and removes the provider and its imported voices.
Unsaved form changes are kept until you save or explicitly discard them.

### Keys and voices

After updating an existing installation, run `python manage.py migrate` in the
backend (or `docker compose exec video_creator python manage.py migrate` from
`backend/`). The provider-name migration updates saved voice records to `OPENAI`,
`ELEVENLABS`, and `SIXTYDB`. Until it is applied, existing service voices with old
provider names will not appear in the picker.

Restart running Celery services after updating backend code so they load the current
provider registry and tasks: `docker compose restart celery celery-beat` from
`backend/`. Existing workers keep their previously loaded code until restarted.

The built-in voices you can pick follow the keys you hold:

- **A provider with no key is hidden.** No OpenAI key — service or your own, whichever
  the switch selects — and the OpenAI voices disappear from the picker, from the "Any
  voice" fallback, and from a hand-crafted API request. Clear every key and the list is
  empty for built-in providers. Custom voices remain available under your own-key
  mode if you have configured a custom provider.
- **Saving an ElevenLabs or 60dB key imports that account's voices.** A background job
  picks them up a moment after you save, so they appear on the next reload. They are
  yours: nobody else sees them, and re-saving the same key does not duplicate them.
- **Voices follow the account that owns them, in both directions.** An ElevenLabs
  `voice_id` belongs to the account that minted it, so the picker only ever shows the
  ones your current key can actually reach: your imported voices while the switch is
  on *Use my own keys*, and the ones `setup_elevenlabs`/`setup_60db` imported with the
  service key while it is off. Neither set is offered with the wrong key behind it.

The OpenAI voices the fixtures ship are shared with everyone, because `alloy` and the
rest are built-in names that work with any OpenAI key — unlike an ElevenLabs voice,
which is minted inside one account.

Encryption uses `FIELD_ENCRYPTION_KEY`, which is derived from `SECRET_KEY` when it is
not set. That is fine locally, but on anything you intend to keep, set it explicitly
and never change it afterwards — rotating it (or rotating `SECRET_KEY` while it is
unset) makes every stored key undecryptable. Generate one with:

```shell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Notifications

Generation and rendering take minutes, so the bell in the top right tells you when one
of your videos is done — or when it stopped. Each entry links to the video it is about,
and the badge counts what you have not read yet.

![The notification bell](docs/screenshots/navigation-notifications.png)

You still get the same thing by email, so closing the tab is safe either way.

## Creating a video

The generation page separates your story from its voice and visuals. Write a prompt,
use one of the example ideas, or choose **Start from a template**. Pick a presenter
or a voice, then choose web images or AI-generated visuals and their provider.

The **Your video** panel summarizes those choices and contains **Generate video**.
Narration can be turned off for a video made from clips only. **Advanced settings**
contains the target audience, genre, script model, background music URL, and subtitles.
The layout stacks vertically on smaller screens.

![Advanced generation settings](docs/screenshots/generation-settings.png)

Generation creates a draft first. Review its scenes in the editor before rendering
it into a finished video.

## Templates

A template is a saved copy of the generation form — the prompt and every setting under
it. Fill the form in and use **Save as template** in the **Your video** panel to name
and keep it. Picking it from **Start from a template** later fills the whole form back
in, and **Delete** next to that dropdown deletes the currently selected template.

![Naming a template](docs/screenshots/save-template.png)

Picking one fills the form back in, and **Delete** beside the dropdown removes it:

![A saved template selected, with the delete button beside it](docs/screenshots/template-saved.png)

Templates are per user: nobody else sees yours, and two people can each keep one called
*Shorts* without colliding. A name has to be unique within your own templates, so saving
over an existing name is refused rather than silently replacing it — delete the old one
first, or pick another name.

## Navigation

The main menu links to generation, your videos, avatars, assets, and providers.
It highlights the current section and collapses into a menu on smaller screens. The
account menu, notifications, and theme switch are available in the header.

![Main navigation and account menu](docs/screenshots/navigation.png)

## Your videos

Search your library by title and use the status badges to see what is ready, finished,
or still being worked on. **Edit scenes** opens the editor; **Watch** previews a
finished video. The actions menu includes details, rendering, resuming, and deletion.
**Create video** starts a new story.

![The videos list](docs/screenshots/videos.png)

A generation that stopped early is not a dead end. **Carry on generating** in its
actions menu carries it on from
where it got to — only the lines with no narration and the shots with no image are made
again, so nothing already generated is paid for twice.

![The resume action on a failed video](docs/screenshots/videos-carry-on-action.png)

![Confirming a resume](docs/screenshots/videos-carry-on-confirmation.png)

## Editing a video

Open a video from the list and every scene is there to change before you render: the
narration line and its audio, the image behind it, and the order they play in. Scenes
can be added, edited, regenerated or removed one at a time, so a single bad shot does
not mean generating the whole thing again.

![Editing a generated video scene by scene](docs/screenshots/video-edit.png)

Use the scene navigator to jump between numbered scene cards. **Edit text** opens
the dialogue editor, where you can review an AI rewrite before saving. **Edit visual**
lets you upload an image or video with a preview, or generate a new image.

**Settings** opens the video's intro, outro, avatar and subtitle controls.
**Render video** queues the render once the video is ready. While rendering, the
button stays disabled.

If narration is missing, an amber notice lists the affected scenes. **Retry narration**
on a scene regenerates its audio while keeping the dialogue and visual. The render
dialog also checks for missing narration: cancel to retry it, or choose **Render anyway**
to use the available audio. Videos with narration turned off do not show this warning.

| | |
| --- | --- |
| ![Video settings](docs/screenshots/editor-video-settings.png) | ![Queue a render](docs/screenshots/editor-render-confirmation.png) |
| **Video settings** — intro, outro, avatar, subtitles | **Render** — warns about missing narration, then queues the job |
| ![Edit a scene](docs/screenshots/modal-edit-scene.png) | ![Edit a scene image](docs/screenshots/modal-edit-image.png) |
| **Edit scene** — rewrite the line and resynthesise it | **Edit scene image** — replace it, or regenerate from a new description |
| ![Add a scene](docs/screenshots/editor-add-scene.png) | ![Delete a scene](docs/screenshots/editor-delete-scene.png) |
| **Add scene** — write a line and upload or generate its visual | **Delete** — the same confirmation guards scenes, images, videos and assets |

## Avatars and assets

An avatar is a face plus the voice that speaks for it; SadTalker animates it against
the narration. Search your presenters by name and preview their voices from each card.
**Create avatar** pairs a portrait upload with a voice and lets you preview the portrait
before saving.

![Avatar library](docs/screenshots/avatars.png)

**My assets** keeps reusable intro and outro clips in separate tabs. Search each
collection, preview a clip, or upload a new one with a name and video preview. Pick
your intro and outro in the video settings.

![Intro and outro assets](docs/screenshots/assets.png)

| | |
| --- | --- |
| ![Create a new avatar](docs/screenshots/modal-new-avatar.png) | ![Add an asset](docs/screenshots/modal-new-asset.png) |
| **New avatar** — name, gender, voice and a face to animate | **New asset** — upload an intro or outro clip |

## Twitch compilations

Twitch video generation is temporarily disabled. It is hidden from navigation, its
page displays an unavailable message, and the generation API rejects new requests
without creating a video or queueing a job. Existing Twitch videos remain in your
library.

## Frontend API requests

Frontend requests use `src/api/request.js` through the helpers in `src/api/apiService.js`.
Every helper returns `{ ok, data, status, message, errors }` plus response headers.
JSON objects and multipart uploads use Axios content-type handling, and search and
pagination values are sent as query parameters. Callers that display their own
validation errors suppress the shared error notification.

## Architecture

For how a request becomes a video — the generation and render pipelines, the status
state machine, resume, and where to add a provider — see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## API Documentation

You can find all API endpoints in Swagger: [http://localhost:3000/swagger/](http://localhost:3000/swagger/)
under Docker, or [http://localhost:8000/swagger/](http://localhost:8000/swagger/) against
`runserver`.

![Swagger](docs/screenshots/swagger.png)

---

## Roadmap / To-Do List

- [ ] Convert all `moviepy` functions to `FFmpeg` for better performance.
- [x] Add **Celery** support for asynchronous and scheduled tasks.
- [x] Implement unit tests for models, functions, and views.

---

## Contact & Support

For any inquiries or support, feel free to reach out:

- University Email: [kodamia@cs.ihu.gr](mailto:kodamia@cs.ihu.gr)
- Personal Email: [kostas2372@gmail.com](mailto:kostas2372@gmail.com)

---

## Recent Updates

✅ Save the generation form as a named template and pick it again later, with a delete button beside the picker\
✅ Fixed the "video completed" and "video failed" emails, which went out addressed to the subject line rather than to you\
✅ Fixed pressing render on a finished video reporting success before the render had started\
✅ Redesigned the generation form with visible voice and visual controls, advanced settings, and a live creation summary\
✅ Added a dedicated custom voice providers tab, with connection and authentication settings, voice imports, and credential management\
✅ Added per-user API keys, managed from the app and stored encrypted, so a user can spend their own quota instead of the service keys\
✅ Voices now follow your keys — your ElevenLabs/60dB voices import themselves, and a provider you hold no key for is hidden instead of failing mid-render\
✅ Added a voice picker to the generation form for videos made without an avatar\
✅ Added password reset by email\
✅ Merged the frontend into this repository and added it to Docker, served on one origin\
✅ Migrated image generation from the retired DALL-E to the `gpt-image` models\
✅ Refreshed the OpenAI model list (gpt-4.1 / gpt-5 families and the o-series)\
✅ Dropped local coqui TTS — all voices are API-backed now, and the image is far smaller\
✅ Builds and runs natively on arm64 (Apple Silicon) as well as x86\_64\
✅ Fixed subtitles: they render over the video instead of as a black bar\
✅ Fixed rendered audio being unplayable in Safari/QuickTime (mp3-in-mp4 → aac)\
✅ Added support for Gemini and Claude AI models\
✅ Integrated ElevenLabs API voices\
✅ Integrated 60dB API voices\
✅ Enabled compilation video creation from Twitch (by game or streamer)\
✅ Added OpenAI voices\
✅ Integrated MidJourney and Stable Diffusion as image providers *(Change providers in ****\`\`****)*\
✅ Dockerized the application for easier deployment

---
