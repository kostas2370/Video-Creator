#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset


# The migrations are committed, so this is normally a no-op. The app labels stay
# because a bare `makemigrations` silently skips any app whose migrations package is
# missing — reporting "No changes detected" and leaving migrate with no tables to
# create, which is how a fresh checkout used to fail on the loaddata below.
python manage.py makemigrations usermanagement videomanagement
python manage.py migrate
python manage.py loaddata fixtures/production_fixtures.json
python manage.py setup_media
python manage.py setup_elevenlabs

python manage.py runserver 0.0.0.0:8000
