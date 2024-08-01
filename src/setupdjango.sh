#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

cd ../src
ls
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata fixtures/production_fixtures.json
python manage.py setup_media
python manage.py setup_elevenlabs

