#!/bin/bash

set -o errexit
set -o nounset

rm -f './celerybeat.pid'

celery -A video_creator worker -l INFO --pool=solo
