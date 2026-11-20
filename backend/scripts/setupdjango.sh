#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# Explicit development/bootstrap setup, separate from production startup.
python manage.py migrate --noinput
python manage.py loaddata fixtures/fixtures.json
python manage.py setup_media
if [ "${MUSIC_CATALOG_AUTO_SETUP:-true}" = "true" ]; then
  python manage.py setup_music_catalog --best-effort
fi
python manage.py setup_elevenlabs
