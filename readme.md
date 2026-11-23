# [RSSPol](https://feed.dony.me "RSS Feed Generator")

[![Latest Release](https://img.shields.io/github/v/release/ashcoft/pol)](https://github.com/ashcoft/pol/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-%E2%89%A53.12-blue?logo=python&logoColor=white)](https://python.org)
[![Django Version](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)](https://www.djangoproject.com)
[![PostgreSQL Version](https://img.shields.io/badge/PostgreSQL-19-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Docker Image](https://img.shields.io/badge/ghcr.io-ashcoft%2Fpol-2496ED?logo=docker&logoColor=white)](https://github.com/ashcoft/pol/pkgs/container/pol)

[![Tests](https://img.shields.io/github/actions/workflow/status/ashcoft/pol/ci.yml?label=tests)](https://github.com/ashcoft/pol/actions/workflows/ci.yml)
[![E2E tests](https://img.shields.io/github/actions/workflow/status/ashcoft/pol/e2e.yml?label=e2e)](https://github.com/ashcoft/pol/actions/workflows/e2e.yml)
[![Docker publish](https://img.shields.io/github/actions/workflow/status/ashcoft/pol/docker-publish.yml?label=docker)](https://github.com/ashcoft/pol/actions/workflows/docker-publish.yml)
[![Snyk security](https://snyk.io/test/github/ashcoft/pol/badge.svg)](https://snyk.io/test/github/ashcoft/pol)

RSS feed generator website with user friendly interface.

![PolitePaul](frontend/frontend/assets/frontend/images/apple-touch-icon-144x144-precomposed.png "PolitePaul")

Source code based on [https://github.com/taroved/pol](https://github.com/taroved/pol) of an RSS feed generator website with a user friendly interface: enter a page URL, pick the elements that make up a feed, and get a ready-to-use RSS feed. A live deployment is available at [feed.dony.me](https://feed.dony.me).

## Repository layout

```
pol/                       downloader core (Twisted HTTP server, feed builder, client, db helpers, log, GC monitor)
pol/reader/                feed reader: discovery, parsing, full text, caches, output formats, CLI
frontend/                  Django app (models, views, templates, forms, migrations, fixtures, settings.py.example)
frontend/frontend/assets/  static assets (LESS/SASS, CSS, JS, images)
nginx/                     host nginx template (default.site-example)
tests/                     pytest test suite
.github/workflows/         CI, Docker publish, release, Snyk, Pullfrog
requirements.txt           pinned Python dependencies
Dockerfile                 production image (Python 3.15)
docker-compose.yaml        app + PostgreSQL 19
docker-compose.prod.yml    pull-only production compose (no build)
.env.example               production environment template
.dockerignore
wait-for-it.sh             optional PostgreSQL wait wrapper
downloader.py
```

## Feed reader features

Besides scraping a page into a new feed, pol can read, enrich and re-export
existing feeds:

* Read RSS 0.9x/2.0, Atom 0.3/1.0, RDF (RSS 1.0) and JSON Feed 1.0/1.1.
* Discover feeds on a page, ported from [ashcoft/rss-finder](https://github.com/ashcoft/rss-finder):
  `<link rel="alternate">`, feed-looking anchors, well-known paths under the
  page and then under the site root, and every candidate is verified by parsing it.
* Fetch the full article text for feed items (readability-style extraction,
  or a manual XPath).
* Build feeds from JSON, HTML or XML documents with hand-written rules.
* Export as RSS 2.0, JSON Feed, CSV, HTML or JSONP.
* HTTP caching with memory, redis or the built-in disk cache (`diskcache`
  backend) and `ETag`/`Last-Modified` revalidation.
* Replace tracking links with direct links, including known redirect wrappers
  (`l.facebook.com`, `google.com/url`, `news.google.com`, `translate.google.*`,
  `getpocket.com/redirect`, `out.reddit.com`, ...), feedsportal links and
  feedburner `origLink` values.
* Recover broken encodings (BOM, header, XML declaration, meta charset, legacy
  Chinese/Japanese/Korean/Cyrillic code pages).
* Follow HTTP redirects and `<meta http-equiv="refresh">` redirects.
* Same features from a `morss`-style command line.

The index page accepts `?q=<page url>` (for example
`/?q=https://www.cyclingnews.com`) to prefill the search box. Discovery is
protected by a self-hosted Cap proof-of-work challenge, so the user
completes the verification widget and then presses **Find RSS**. Each result
has a **Preview** action that opens a slide-in pane with the latest feed items,
plus **Copy** and **Open** actions, mirroring the rss-finder interface.

## Reader HTTP API

The downloader server exposes these endpoints. Django serves the two
discovery endpoints so it can require a captcha, then proxies them to the
downloader; the preview endpoint goes straight to the downloader. nginx routes
each path accordingly (see `nginx/default.site-example`):

| Endpoint | Description |
| --- | --- |
| `GET /read?url=<feed>` | Read a feed, or discover one on an HTML page. |
| `GET /read?url=<feed>&format=json\|csv\|html` | Same, in another format. |
| `GET /read?url=<feed>&callback=cb` | JSONP output. |
| `GET /discover?url=<page>` | `{"feeds": [{"title", "url", "type"}]}` (rss-finder shape). Captcha required. |
| `GET /api/find-feeds?url=<page>` | Alias of `/discover`. Captcha required. |
| `POST /api/find-feeds` | JSON body `{"url": "..."}` plus a solved Cap `cap-token` field. |
| `GET /api/feed-preview?url=<feed>` | Feed metadata and the latest items as JSON. |

The discovery endpoints require a solved Cap token. Load the index page,
complete the Cap widget, then send its hidden `cap-token` field with the URL.
Cap is self-hosted: the compose stack runs `capd` and Valkey. Create a site key
in the capd dashboard (`CAP_PUBLIC_URL`, log in with `CAP_ADMIN_KEY`), then set
`CAP_SITE_KEY` and `CAP_SECRET` in `.env`. `CAP_PUBLIC_URL` is the browser-facing
capd origin; `CAP_API_URL` is the server-to-server origin (default
`http://cap:3000`). `CAP_TEST_MODE` is for the E2E stack only.

Site keys live in Cap's Valkey volume. If that volume is reset, create a new
key in the dashboard and update `CAP_SITE_KEY` / `CAP_SECRET`, then recreate
the app. Behind nginx, set the capd visitor IP header to `X-Forwarded-For` so
Cap sees the real client IP instead of the proxy's.

`/read` parameters: `format`, `callback`, `fulltext`/`fill`, `proxy`, `clip`,
`resolve`, `search`, `order`, `firstlink`, `nolink`, `noref`, `xpath`, `indent`,
`max_items`, `offline`, `force`, `no_meta`, plus the custom-feed rules `mode`,
`items`, `item_title`, `item_link`, `item_content`, `item_desc`, `item_time`,
`item_author`, `item_image`. Full-text fetching is off by default on HTTP and
can be enabled with `fulltext=1`.

The examples use the host nginx URL. In development the downloader alone
listens on `1234`.

Examples:

```bash
curl 'http://localhost/read?url=https://example.com/feed.xml'
curl 'http://localhost/read?url=https://example.com/feed.xml&format=json&fulltext=1'
```

Feed discovery needs a solved Cap token, so use the web interface or submit
the widget's `cap-token` field explicitly.

## Command line

```bash
python -m pol.reader https://example.com/feed.xml --format json --indent
python -m pol.reader https://example.com/ --discover
python -m pol.reader https://example.com/feed.xml --fulltext --resolve --cache \
    --cache-backend diskcache --cache-dir /var/cache/pol
python -m pol.reader https://example.com/api \
    --mode json --items 'data.posts[]' --item-title title \
    --item-link url --item-content body --format rss
```

Installing the project (`pip install .`) also provides the `morss` and
`pol-feed` console scripts.

The morss options are accepted too: `--post STRING` sends the body to the feed
URL, `--order first|last|newest|oldest` chooses which items are enriched when
`--max-items` is reached (the output order is unchanged), `--firstlink` takes
the item link from the first `<a>` in the description, `--nolink` drops anchors
from item content while keeping their text, `--noref` drops item links, and
`--silent` suppresses the output.

## Cache backends

Set `POL_CACHE_BACKEND` (or `CACHE_BACKEND` in `settings.py`) to `memory`
(default), `diskcache`, `redis` or `none`. The `diskcache` backend is a built-in
JSON-backed disk cache (no extra package); `POL_CACHE_DIR` selects its directory.
`POL_REDIS_URL` selects the redis server. The reader uses conditional requests
(`If-None-Match` / `If-Modified-Since`) and falls back to the memory backend
when Redis is unavailable.

## Requirements and pinned versions

The production image and CI are built and tested with:

| Component | Version / requirement |
| --- | --- |
| pol | 1.3.1 (source); production image is `latest` or `POL_VERSION` until the next release |
| Python | 3.15 (`python:3.15-slim`) |
| Django | 6.1.3 |
| PostgreSQL | 19 (`postgres:19`) |
| nginx | 1.28.3 (Ubuntu Server 26.04 LTS host package) |
| Docker Compose | v2 (required) |

The application version is 1.3.1. The `1.3.1` image predates the host-nginx
layout, so `docker-compose.prod.yml` uses `ghcr.io/ashcoft/pol:latest` until a
release containing this change is published. Set `POL_VERSION` in `.env` to pin
that release tag. `docker-compose.yaml` also tracks `latest` for development.
Python packages are pinned in
`requirements.txt`. The Dockerfile pins the Python base image tag, and both
compose files pin `postgres:19`. nginx is not in the compose stack: use the
Ubuntu Server LTS package on the host (1.28.3 on 26.04) with the included
template. Pin the base image digest if you need byte-for-byte reproducible
builds. Set `POL_VERSION` to the new release tag and update this table when a
release is published.

System build dependencies for `psycopg`, `lxml` and Scrapy, e.g. on Ubuntu/Debian:

```bash
sudo apt-get install build-essential pkg-config libpq-dev libxml2-dev libxslt1-dev libffi-dev libssl-dev gettext
```

Optional, only if you rely on Django Pipeline's LESS/SASS compilation instead of prebuilt assets:

```bash
sudo apt-get install nodejs npm
sudo npm install -g less
sudo apt-get install ruby ruby-dev
sudo gem install sass
```

## Development server (Ubuntu)

Set up Python environment and install dependencies(from the repo root):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install pytest
```

Create the Django settings module (the repo expects `settings.py` next to the
`frontend` package; it is git-ignored):

```bash
cp frontend/frontend/settings.py.example frontend/frontend/settings.py
```

Create the database:

```bash
createdb pol    # or: psql -U postgres -c 'CREATE DATABASE pol;'
```

If your local PostgreSQL differs from the settings defaults, export `DB_NAME`,
`DB_USER`, `DB_PASSWORD`, `DB_HOST` and `DB_PORT` before running the servers.
The non-Docker settings defaults are `pol` / `postgres` / `postgres` on
`127.0.0.1:5432`. `.env.example` is the Docker template and uses `pol` / `pol` /
`change-me`.

Initialise the database:

```bash
cd frontend
python manage.py migrate
python manage.py loaddata fields.json
cd ..
```

(If you have some questions, please contact the author via the GitHub email.)

### Run the servers

Run the downloader/RSS server (default port `1234`):

```bash
python downloader.py
```

Run the Django frontend:

```bash
python frontend/manage.py runserver
```

For the frontend to reach the downloader (`/downloader`, `/feed`, `/feed1`),
install nginx and use the included site template:

```bash
sudo apt-get install nginx
sudo cp nginx/default.site-example /etc/nginx/sites-available/pol
sudo ln -s /etc/nginx/sites-available/pol /etc/nginx/sites-enabled/pol
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

The template proxies `/` to the Django server on port 8000 (Gunicorn in
production). It also sends `/discover` and `/api/find-feeds` to Django so the
captcha check runs, while `/downloader`, `/feed`, `/feed1`, `/read`, `/rss` and
the rest of `/api/` (the preview endpoint) go to the downloader on port 1234.
The Docker stack publishes those same loopback ports for the host nginx. The
stack also runs `capd` on `127.0.0.1:3000`; use `nginx/cap.site-example` for the
browser-facing Cap origin and set `CAP_PUBLIC_URL` to it.

The template forwards the browser `Host` header so Django's CSRF checks pass
behind the proxy. If you reach the app by anything other than
`localhost`/`127.0.0.1`, export `ALLOWED_HOSTS` (comma separated) with that name
or IP before starting Django.

## Docker

The production image is `ghcr.io/ashcoft/pol:latest` until the next release.
Set `POL_VERSION` in `.env` to pin a release tag. `docker-compose.yaml` also
uses `latest` for development.

`latest` is rebuilt by the `Publish Docker image` workflow on every push to
`main`. After the host-nginx change lands, wait for that workflow to finish
before pulling `latest`; otherwise use `docker compose up -d --build` so the
image matches this checkout. The `1.3.1` release predates the host-nginx layout
and must not be used with this compose file.

```bash
git clone https://github.com/ashcoft/pol.git
cd pol
cp .env.example .env      # optional; edit the values
docker compose up -d
```

Compose tries to pull `ghcr.io/ashcoft/pol:latest` first. If the pull succeeds,
the image is used and nothing is built. If the pull fails (the package is
private, you are not logged in, or the image is not published yet), Compose
falls back to building the local `Dockerfile` because the service also has a
`build:` section. Use `docker compose up -d --build` to force a local build.

The GHCR package is private by default. Log in once with a token that has
`read:packages`:

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u <your-github-username> --password-stdin
docker compose pull
docker compose up -d
```

Set the package visibility to public in the GitHub package settings if you want
anonymous pulls.

If you never want the build fallback, use the pull-only production file:

```bash
docker compose -f docker-compose.prod.yml up -d
```

It has no `build:` section and uses `POL_PULL_POLICY` (default `always`), so it
pulls the published image and fails explicitly if the registry is unavailable.

If you cannot use GHCR, build the image locally and reuse it with
`POL_PULL_POLICY=never`. Both compose files use the same `POL_VERSION`, so the
local build gets the tag production expects:

```bash
POL_VERSION=$(grep -E '^POL_VERSION=' .env 2>/dev/null | cut -d= -f2-)
docker compose up -d --build
POL_PULL_POLICY=never docker compose -f docker-compose.prod.yml up -d
```

Back up the exact production image so a removed container does not force a
GHCR login:

```bash
POL_VERSION=$(grep -E '^POL_VERSION=' .env 2>/dev/null | cut -d= -f2-)
docker save "ghcr.io/ashcoft/pol:${POL_VERSION:-latest}" \
  | gzip > /tmp/pol-image.tar.gz

# restore later, then start without pulling
gunzip -c /tmp/pol-image.tar.gz | docker load
POL_PULL_POLICY=never docker compose -f docker-compose.prod.yml up -d
```

Set `POL_PULL_POLICY=never` in `.env` if every production start should use the
local image.

The stack starts two services:

* `politepol` - `ghcr.io/ashcoft/pol:${POL_VERSION:-latest}`;
  Gunicorn and the downloader in one container, running as the unprivileged
  `appuser`; publishes `127.0.0.1:8000` and `127.0.0.1:1234` on the host
* `dbpolitepol` - `postgres:19`, with its data in the `pol_pg` volume mounted
  at `/var/lib/postgresql`

The compose stack does not run nginx. Use the nginx from Ubuntu Server LTS
(1.28.3 on 26.04) with the included template; it proxies `/`, `/discover` and
`/api/find-feeds` to `127.0.0.1:8000` and `/downloader`, `/feed`, `/feed1`,
`/read`, `/rss` and the rest of `/api/` to `127.0.0.1:1234`.

At start, `frontend/start.sh` waits for PostgreSQL, runs `migrate` and
`loaddata`, then starts the downloader and Gunicorn. `settings.py` is generated
at image build and reads the environment at import. `collectstatic` runs at
image build; WhiteNoise serves `/static/` through Gunicorn.

Compose fixes `DB_HOST=dbpolitepol` and `DB_PORT=5432`; PostgreSQL always listens
on 5432 inside the container. The app's settings still read `DB_HOST`/`DB_PORT`
for non-Docker runs.

PostgreSQL 19 stores its cluster under `/var/lib/postgresql/19/docker`, so the
`pol_pg` volume is mounted at `/var/lib/postgresql`, the layout the official
image expects. If you have data from an older `/var/lib/postgresql/data` mount,
dump it and restore it into a fresh volume before switching.

Compose reads `.env` for these values:

| Variable | Default | Meaning |
| --- | --- | --- |
| `DB_NAME` | `pol` | database name |
| `DB_USER` | `pol` | database user |
| `DB_PASSWORD` | `change-me` | database password |
| `POL_VERSION` | `latest` | app image tag to pin in production |
| `POL_PULL_POLICY` | unset | pull policy; production defaults to `always`, development to `missing` |
| `TIME_ZONE` | `UTC` | Django timezone |
| `DEBUG` | `False` | keep `False` in production |
| `SECRET_KEY` | `change-me-in-production` | set a long random value |
| `ALLOWED_HOSTS` | loopback | comma-separated public hostnames |
| `CSRF_TRUSTED_ORIGINS` | empty | e.g. `https://feeds.example.com` |
| `GUNICORN_WORKERS` | `3` | Gunicorn worker processes |
| `GUNICORN_THREADS` | `4` | threads per worker |
| `GUNICORN_TIMEOUT` | `120` | Gunicorn timeout in seconds |

Example `.env` for a public HTTPS site:

```dotenv
DB_PASSWORD=change-me
DEBUG=False
SECRET_KEY=put-a-long-random-value-here
ALLOWED_HOSTS=feeds.example.com
CSRF_TRUSTED_ORIGINS=https://feeds.example.com
```

### Host nginx (Ubuntu Server LTS)

Install nginx from the Ubuntu repository and use the included template:

```bash
sudo apt-get install nginx
sudo cp nginx/default.site-example /etc/nginx/sites-available/pol
sudo ln -s /etc/nginx/sites-available/pol /etc/nginx/sites-enabled/pol
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

The template listens on port 80 and proxies to the loopback ports published by
Compose. For HTTPS:

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d feeds.example.com
```

Then set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to the public HTTPS host.

### Operations

```bash
# logs
docker compose logs -f politepol

# upgrade
docker compose pull
docker compose up -d

# pull-only production file
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# database backup
docker compose exec -T dbpolitepol sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > pol.sql

# image backup (for hosts that cannot pull from GHCR)
POL_VERSION=$(grep -E '^POL_VERSION=' .env 2>/dev/null | cut -d= -f2-)
docker save "ghcr.io/ashcoft/pol:${POL_VERSION:-latest}" \
  | gzip > /tmp/pol-image.tar.gz
gunzip -c /tmp/pol-image.tar.gz | docker load
POL_PULL_POLICY=never docker compose -f docker-compose.prod.yml up -d
```

### Publishing the image (maintainers)

`.github/workflows/docker-publish.yml` runs on pushes to `main` and `v*` tags:

- `ghcr.io/ashcoft/pol:latest` on the default branch
- `ghcr.io/ashcoft/pol:sha-<short>` on every push
- `ghcr.io/ashcoft/pol:<version>` and `<major>.<minor>` for `v*` tags

The package must be linked to the `ashcoft/pol` repository. If it is not, the
workflow fails with `denied: permission_denied: read_package`. Link it in the
package settings (Repository source -> Connect repository), then re-run the
workflow. Packages are private by default.

### Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `docker compose up` starts a build (using `docker-compose.yaml`) | GHCR pull failed (private package, not logged in, or not published) | `docker login ghcr.io`, then `docker compose pull`; or use `--build` for a local build |
| `Head ... unauthorized` on pull | Private package and no login | Log in with a `read:packages` token |
| `permission_denied: read_package` in Actions | Package is not linked to the repository | Link the package in its settings and re-run the workflow |
| App waits for the database and exits | PostgreSQL not ready or wrong credentials | `docker compose logs dbpolitepol`; check `DB_*` in `.env` |
| `dbpolitepol` exits with "PostgreSQL data in /var/lib/postgresql/data" | Volume created with the old mount | Dump it first if you need the data, then `docker compose down -v` and start fresh |
| Host nginx returns 502 | App ports not reachable | `docker compose ps`; the app must publish `127.0.0.1:8000` and `127.0.0.1:1234` |

## Tests

```bash
cp frontend/frontend/settings.py.example frontend/frontend/settings.py
pip install pytest
pytest tests/
```

CI runs `pytest -v tests/` on Python 3.15, plus linting, a Docker image build and
an import check inside the image. The tests do not need a database; the Django
tests load settings only.

## End-to-end tests

The Playwright suite runs against a live stack. Start the downloader with the
private-host reader flag so the local fixture is reachable:

```bash
# terminal 1
POL_READER_ALLOW_PRIVATE=1 python downloader.py 1234

# terminal 2
python -m gunicorn frontend.wsgi:application \
  --pythonpath ./frontend --bind 127.0.0.1:8000

# nginx: copy nginx/default.site-example to sites-available/default and start it
```

Then:

```bash
pip install -r requirements-e2e.txt
python -m playwright install --with-deps chromium
RUN_E2E=1 pytest tests/e2e -v
```

`tests/e2e` uses a local HTTP fixture, so it does not call external sites.
`E2E_BASE_URL` selects the URL (default `http://127.0.0.1`). The `E2E` workflow
starts the full stack and runs the same command; the normal CI run ignores
`tests/e2e`.

## License

MIT
