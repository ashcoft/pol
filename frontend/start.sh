#!/bin/bash
set -e

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

python frontend/manage.py migrate --noinput
python frontend/manage.py loaddata fields.json || echo 'fixtures already loaded'

python downloader.py 1234 &

exec python -m gunicorn frontend.wsgi:application \
    --pythonpath ./frontend \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile -
