#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

python manage.py check --deploy --fail-level ERROR
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py collectstatic --noinput
