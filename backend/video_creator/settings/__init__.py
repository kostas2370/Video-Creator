"""Environment-aware settings package.

`DJANGO_SETTINGS_MODULE` stays `video_creator.settings` everywhere it is already
spelled out — manage.py, wsgi.py, asgi.py, celery.py, CI — and this module picks the
right environment from ENV, so none of those entrypoints has to know about the split:

    ENV=prod                     -> video_creator.settings.production
    anything else (the default)  -> video_creator.settings.local

Pointing DJANGO_SETTINGS_MODULE straight at `video_creator.settings.production` also
works, for a deployment that would rather be explicit than rely on ENV.

The .env file is loaded here rather than in base.py: ENV itself usually comes from it,
so it has to be on os.environ before the branch below is taken.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

ENV = os.getenv("ENV", "dev")

if ENV == "prod":
    from .production import *  # noqa: F401,F403
else:
    from .local import *  # noqa: F401,F403
