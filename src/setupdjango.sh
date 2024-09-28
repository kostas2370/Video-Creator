#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

cd ../src

echo "Waiting for MySQL database..."

while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
  echo "Waiting for MySQL to be ready at $DB_HOST:$DB_PORT..."
done

echo "MySQL is up and running at $DB_HOST:$DB_PORT!"

# Execute the following command passed to the script (e.g., starting Django)
exec "$@"


python manage.py migrate
python manage.py loaddata fixtures/production_fixtures.json
python manage.py setup_media
python manage.py setup_elevenlabs

