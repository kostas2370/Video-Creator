#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

cd ../src
ls
# App labels kept deliberately — see the note in startdjango.sh.
python manage.py makemigrations usermanagement videomanagement
python manage.py migrate
python manage.py loaddata fixtures/production_fixtures.json
python manage.py setup_media
python manage.py setup_elevenlabs
python manage.py setup_checkpoints

