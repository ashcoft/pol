# syntax=docker/dockerfile:1
FROM python:3.15-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps for mysqlclient, lxml and the downloader stack.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        default-libmysqlclient-dev \
        libxml2-dev \
        libxslt1-dev \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt \
    && pip install mysqlclient


FROM python:3.15-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    WEB_PORT=8088

# Runtime deps only: nginx for the same-origin proxy, shared libraries for
# the Python packages built above.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        nginx \
        curl \
        tini \
        ca-certificates \
        libmariadb3 \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY . .

# The app expects a settings module next to the frontend package, and nginx
# needs the site template that proxies / to Django and /feed to the downloader.
RUN cp ./frontend/frontend/settings.py.example ./frontend/frontend/settings.py \
    && cp ./nginx/default.site-example /etc/nginx/sites-available/default \
    && sed -i 's|location / {|location /static/ {\n                alias /app/frontend/frontend/static/;\n        }\n\n        location / {|' \
              /etc/nginx/sites-available/default \
    && chmod +x ./frontend/start.sh \
    && mkdir -p /tmp /var/lib/nginx/body /var/lib/nginx/proxy /var/lib/nginx/fastcgi \
                /var/lib/nginx/uwsgi /var/lib/nginx/scgi \
    && chown -R appuser:appuser /app /etc/nginx /var/lib/nginx /var/log/nginx /tmp

USER appuser

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD sh -c 'host="${ALLOWED_HOSTS:-127.0.0.1}"; \
               curl -fsS -H "Host: ${host%%,*}" "http://127.0.0.1:${WEB_PORT}/en/" || exit 1'

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["./frontend/start.sh"]
