#!/bin/bash
set -euo pipefail

WEB_PORT="${WEB_PORT:-8088}"

# nginx listens on WEB_PORT and proxies to Django and the downloader.
# The container runs as a non-root user, so keep the pid file in /tmp.
if grep -q '^pid ' /etc/nginx/nginx.conf; then
    sed -i -E 's#^pid .*#pid /tmp/nginx.pid;#' /etc/nginx/nginx.conf
else
    sed -i '1i pid /tmp/nginx.pid;' /etc/nginx/nginx.conf
fi

NGINX_SITE=/etc/nginx/sites-available/default
if [ -f "$NGINX_SITE" ]; then
    sed -i -E \
        -e "s/listen 80/listen ${WEB_PORT}/g" \
        -e "s/\[::\]:80/[::]:${WEB_PORT}/g" \
        "$NGINX_SITE"
fi

# Wait for MySQL to accept connections before migrating.
python - <<'PY'
import os
import sys
import time

import MySQLdb

for attempt in range(60):
    try:
        MySQLdb.connect(
            host=os.environ.get('DB_HOST', '127.0.0.1'),
            port=int(os.environ.get('DB_PORT', '3306')),
            user=os.environ.get('DB_USER', 'root'),
            passwd=os.environ.get('DB_PASSWORD', 'toor'),
            db=os.environ.get('DB_NAME', 'pol'),
        ).close()
        break
    except Exception as exc:  # noqa: BLE001 - retried below
        if attempt == 59:
            sys.exit('database is not reachable: %s' % exc)
        time.sleep(1)
PY

nginx

python ./frontend/manage.py migrate --noinput
python ./frontend/manage.py loaddata fields.json
# Serve the static files from nginx so DEBUG=0 works as well.
python ./frontend/manage.py collectstatic --noinput

python ./downloader.py &
downloader_pid=$!
trap 'kill "$downloader_pid" 2>/dev/null || true' EXIT

exec python ./frontend/manage.py runserver 0.0.0.0:8000 --noreload
