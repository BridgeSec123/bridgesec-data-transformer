#!/bin/sh

echo "Running DB migrations..."
python manage.py migrate

echo "Starting Django with debugger..."
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client manage.py runserver 0.0.0.0:8000
