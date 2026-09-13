#!/bin/bash

set -o errexit
set -o nounset

rm -f './celerybeat.pid'

# The worker is the only service that runs SadTalker, so it is the one that needs the
# model weights. This skips anything already on disk, and /app is the bind mount, so
# the first boot pays the download once and every rebuild after that reuses it.
python manage.py setup_checkpoints

celery -A video_creator worker -l INFO --pool=solo
