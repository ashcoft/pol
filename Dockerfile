# syntax=docker/dockerfile:1

FROM python:3.15-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/pip install -r requirements.txt


FROM python:3.15-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    HOME=/home/appuser \
    WEB_PORT=8088 \
    DEBUG=False

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        nginx \
        libpq5 \
        libxml2 \
        libxslt1.1 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default \
    && useradd --create-home --uid 1000 appuser \
    && mkdir -p /tmp/nginx/conf.d /tmp/nginx/client_body /tmp/nginx/proxy \
        /tmp/nginx/fastcgi /tmp/nginx/uwsgi /tmp/nginx/scgi \
    && chown -R appuser:appuser /tmp/nginx

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN cp frontend/frontend/settings.py.example frontend/frontend/settings.py \
    && cp nginx/default.site-example /etc/nginx/sites-available/default \
    && cp nginx/nginx.conf /etc/nginx/nginx.conf \
    && chmod +x frontend/start.sh wait-for-it.sh \
    && python frontend/manage.py collectstatic --noinput

USER appuser

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${WEB_PORT:-8088}/" > /dev/null || exit 1

CMD ["./frontend/start.sh"]
