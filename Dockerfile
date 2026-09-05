FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Build/runtime deps for mysqlclient, lxml and the downloader stack.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        default-libmysqlclient-dev \
        libxml2-dev \
        libxslt1-dev \
        libffi-dev \
        libssl-dev \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir mysqlclient

COPY . .

# The app expects a settings module next to the frontend package.
RUN cp ./frontend/frontend/settings.py.example ./frontend/frontend/settings.py \
    && chmod +x ./wait-for-it.sh \
    && useradd --create-home --uid 1000 appuser \
    && mkdir -p /tmp && chown -R appuser:appuser /app /tmp

USER appuser

EXPOSE 1234

CMD ["python", "downloader.py", "1234"]
