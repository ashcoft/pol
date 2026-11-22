#!/bin/bash
set -e

WEB_PORT="${WEB_PORT:-8088}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"

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

# nginx is the public listener; Gunicorn and the downloader stay on loopback.
# The image's main nginx config includes /tmp/nginx/conf.d.
mkdir -p /tmp/nginx/conf.d
sed -E \
    -e "s/listen 80 default_server;/listen ${WEB_PORT} default_server;/" \
    -e "s/listen \[::\]:80 default_server;/listen [::]:${WEB_PORT} default_server;/" \
    /etc/nginx/sites-available/default > /tmp/nginx/conf.d/default.conf

python frontend/manage.py migrate --noinput
python frontend/manage.py loaddata fields.json || echo 'fixtures already loaded'

python downloader.py 1234 &
nginx -c /etc/nginx/nginx.conf

exec python -m gunicorn frontend.wsgi:application \
    --pythonpath ./frontend \
    --bind 127.0.0.1:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile -
