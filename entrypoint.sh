#!/bin/bash

# Wait for DB or other services if needed
# echo "Waiting for PostgreSQL..."
# while ! nc -z $DB_HOST $DB_PORT; do sleep 1; done

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
exec gunicorn bridgesec_data_transformer.wsgi:application
       --chdir bridgesec_data_transformer
       --timeout 2000


