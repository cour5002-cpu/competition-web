#!/usr/bin/env sh
set -e

python /app/bootstrap_db.py

exec gunicorn -w ${GUNICORN_WORKERS:-2} -b 0.0.0.0:5000 --timeout ${GUNICORN_TIMEOUT:-120} app:app
