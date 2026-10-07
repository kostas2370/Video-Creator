#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset


# Normally a no-op now the migrations are committed. The app labels stay because a
# bare `makemigrations` silently skips apps whose migrations package is missing.
python manage.py makemigrations usermanagement videomanagement
python manage.py migrate
python manage.py loaddata fixtures/fixtures.json
python manage.py setup_media
python manage.py setup_elevenlabs

exec uvicorn video_creator.asgi:application --host 0.0.0.0 --port 8000 --lifespan off --proxy-headers --forwarded-allow-ips "*"
