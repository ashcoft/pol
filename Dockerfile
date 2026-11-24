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
    DEBUG=False

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libpq5 \
        libxml2 \
        libxslt1.1 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN chmod -R a+rX /app \
    && cp frontend/frontend/settings.py.example frontend/frontend/settings.py \
    && chmod +x frontend/start.sh wait-for-it.sh \
    && python frontend/manage.py collectstatic --noinput

USER appuser

EXPOSE 8000 1234

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:8000/" > /dev/null || exit 1

CMD ["./frontend/start.sh"]
