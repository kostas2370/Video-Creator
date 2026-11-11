#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

cd ../src
ls
# App labels kept deliberately — see the note in startdjango.sh.
python manage.py makemigrations usermanagement videomanagement
python manage.py migrate
python manage.py loaddata fixtures/fixtures.json
python manage.py setup_media
if [ "${MUSIC_CATALOG_AUTO_SETUP:-true}" = "true" ]; then
  python manage.py setup_music_catalog --best-effort
fi
python manage.py setup_elevenlabs
python manage.py setup_checkpoints

