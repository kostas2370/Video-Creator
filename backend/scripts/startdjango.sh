#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset


# Production uses /release once before restarting services.
if [ "${ENV:-dev}" = "prod" ]; then
  python manage.py migrate --check --verbosity 0
else
  /setupdjango
fi

exec uvicorn video_creator.asgi:application --host 0.0.0.0 --port 8000 --lifespan off --proxy-headers --forwarded-allow-ips "*"
