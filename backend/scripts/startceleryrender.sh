#!/bin/bash
set -o errexit
set -o nounset

# Exports with presenters need the same optional model weights as generation.
python manage.py setup_checkpoints
exec celery -A video_creator worker -l INFO --pool=solo -Q renders -n renders@%h
