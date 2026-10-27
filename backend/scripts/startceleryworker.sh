#!/bin/bash

set -o errexit
set -o nounset

# General jobs do not render presenters, so they need no model downloads.
exec celery -A video_creator worker -l INFO --pool=solo -Q celery -n general@%h
