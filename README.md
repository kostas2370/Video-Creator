# Viddie - AI-Powered Video Creation

## Short Description
Viddie is an AI-powered platform for automated video creation, utilizing advanced machine learning models. It streamlines video production by combining OpenAI GPT models for script generation, API text-to-speech (OpenAI, ElevenLabs or 60db) for speech synthesis, OpenAI `gpt-image` models for image generation, and SadTalker for avatar animation. This allows users to generate high-quality videos with minimal manual effort.

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

## How to Run the Project

There are two ways to run the project: manually or using Docker.

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

3. Inside the viddie folder, create a `.env` file (see `backend/.env_example`) and add the
   following API keys:

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

   Voices are all API-backed — OpenAI, ElevenLabs or 60db. The fixtures load the six
   OpenAI voices, so `OPEN_API_KEY` alone is enough to render speech. Local on-device
   synthesis (coqui/TTS) has been removed: it pinned the project to a dependency tree
   that no longer resolves on Python 3.9, and it was the single largest contributor to
   the image size.

5. (Optional) To enable ElevenLabs voices, add your `XI_API_KEY` in the `.env` file and run:

   ```shell
   py manage.py setup_elevenlabs
   ```

6. (Optional) To enable 60db voices, add your `SIXTYDB_API_KEY` in the `.env` file and run:

   ```shell
   py manage.py setup_60db
   ```

   This imports your 60db voices into the database. Once imported, a 60db voice can be
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

### Docker Installation

1. Create the `.env` file and add your OPEN\_API\_KEY, SEARCH\_ENGINE\_ID, API\_KEY as per `.env_example`.
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

## Admin Panel

- URL: [http://localhost:3000/admin/](http://localhost:3000/admin/) under Docker, or
  [http://localhost:8000/admin/](http://localhost:8000/admin/) against `runserver`.
- The fixtures ship no accounts, so create your own — see below.

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

Keys do not have to live in `.env`. Signed in, open the avatar menu in the top right
and choose **API keys** (<http://localhost:3000/api-keys/>) to manage your own from the
browser.

The page has one switch at the top that decides whose keys generation spends:

| Switch | What gets used |
| --- | --- |
| **Use my own keys** — off (default) | The service keys from `.env`. Anything you saved is kept but unused. |
| **Use my own keys** — on | Only the keys saved on this page. |

Below it, every provider the pipeline can reach: OpenAI, Anthropic, Google Gemini,
ElevenLabs, 60dB, Stable Diffusion, Midjourney, Google Custom Search (key and engine
id), and the Twitch client id and secret. Each field saves on its own, so filling one
in never disturbs the rest, and **Clear** empties a single provider while **Remove all
my keys** wipes every one of them.

Two things to know before switching over:

- **There is no fallback.** With your own keys selected, a provider you left blank has
  no key at all — it does not quietly fall back to the service key, and the steps that
  need it will fail. Fill in every provider you actually use.
- **Keys are write-only.** They are stored encrypted and never sent back to the
  browser; a saved key only ever shows masked, as `sk-••••••••ijkl`. That also means
  there is no way to read one back out of the UI — if you lose the original, replace it.

### Keys and voices

The voices you can pick follow the keys you hold, so the list never offers something
that would fail at synthesis:

- **A provider with no key is hidden.** No OpenAI key — service or your own, whichever
  the switch selects — and the OpenAI voices disappear from the picker, from the "Any
  voice" fallback, and from a hand-crafted API request. Clear every key and the list is
  empty.
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

## API Documentation

You can find all API endpoints in Swagger: [http://localhost:3000/swagger/](http://localhost:3000/swagger/)
under Docker, or [http://localhost:8000/swagger/](http://localhost:8000/swagger/) against
`runserver`.

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

✅ Added per-user API keys, managed from the app and stored encrypted, so a user can spend their own quota instead of the service keys\
✅ Voices now follow your keys — your ElevenLabs/60db voices import themselves, and a provider you hold no key for is hidden instead of failing mid-render\
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
✅ Integrated 60db API voices\
✅ Enabled compilation video creation from Twitch (by game or streamer)\
✅ Added OpenAI voices\
✅ Integrated MidJourney and Stable Diffusion as image providers *(Change providers in ****\`\`****)*\
✅ Dockerized the application for easier deployment

---

