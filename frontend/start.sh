#!/bin/bash
set -e

WEB_PORT="${WEB_PORT:-8088}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"

# Wait for the database before running migrations.
python - "$DB_HOST" "$DB_PORT" <<'PY'
import socket
import sys
import time

host, port = sys.argv[1], int(sys.argv[2])
deadline = time.time() + 120
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        time.sleep(2)
else:
    print('database %s:%s is not reachable' % (host, port), file=sys.stderr)
    sys.exit(1)
PY

# Every deployment setting comes from the environment (DB_*, DEBUG, SECRET_KEY,
# ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, TIME_ZONE).
cp frontend/frontend/settings.py.example frontend/frontend/settings.py

# nginx is the public listener; Gunicorn and the downloader stay on loopback.
sed -i -E \
    -e "s/listen 80 default_server;/listen ${WEB_PORT} default_server;/" \
    -e "s/listen \[::\]:80 default_server;/listen [::]:${WEB_PORT} default_server;/" \
    /etc/nginx/sites-available/default

python frontend/manage.py migrate --noinput
python frontend/manage.py loaddata fields.json || echo 'fixtures already loaded'
python frontend/manage.py collectstatic --noinput

setpriv --reuid=appuser --regid=appuser --init-groups python downloader.py 1234 &
nginx -t
nginx

exec setpriv --reuid=appuser --regid=appuser --init-groups \
    python -m gunicorn frontend.wsgi:application \
    --pythonpath ./frontend \
    --bind 127.0.0.1:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile -
