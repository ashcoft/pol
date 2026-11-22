# [RSSPol](https://feed.dony.me "RSS Feed Generator")

RSS feed generator website with user friendly interface.

![PolitePaul](frontend/frontend/assets/frontend/images/apple-touch-icon-144x144-precomposed.png "PolitePaul")

Source code of an RSS feed generator website with a user friendly interface: enter a page URL, pick the elements that make up a feed, and get a ready-to-use RSS feed. A live deployment is available at [feed.dony.me](https://feed.dony.me).

## Repository layout

```
pol/                       downloader core (Twisted HTTP server, feed builder, client, db helpers, log, GC monitor)
pol/reader/                feed reader: discovery, parsing, full text, caches, output formats, CLI
frontend/                  Django app (models, views, templates, forms, migrations, fixtures, settings.py.example)
frontend/frontend/assets/  static assets (LESS/SASS, CSS, JS, images)
nginx/                     nginx configs: default.site-example (host) and nginx.conf (container)
tests/                     pytest test suite
.github/workflows/         CI, Docker publish, release, Snyk, Pullfrog
requirements.txt           pinned Python dependencies
Dockerfile                 production image (Python 3.15 + nginx)
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
`/?q=https://www.cyclingnews.com`) to run discovery immediately. Each result
has a **Preview** action that opens a slide-in pane with the latest feed items,
plus **Copy** and **Open** actions, mirroring the rss-finder interface.

## Reader HTTP API

The downloader server exposes these endpoints (nginx proxies them, see
`nginx/default.site-example`):

| Endpoint | Description |
| --- | --- |
| `GET /read?url=<feed>` | Read a feed, or discover one on an HTML page. |
| `GET /read?url=<feed>&format=json\|csv\|html` | Same, in another format. |
| `GET /read?url=<feed>&callback=cb` | JSONP output. |
| `GET /discover?url=<page>` | `{"feeds": [{"title", "url", "type"}]}` (rss-finder shape). |
| `GET /api/find-feeds?url=<page>` | Alias of `/discover`. |
| `POST /api/find-feeds` | JSON body `{"url": "..."}`. |
| `GET /api/feed-preview?url=<feed>` | Feed metadata and the latest items as JSON. |

`/read` parameters: `format`, `callback`, `fulltext`/`fill`, `proxy`, `clip`,
`resolve`, `search`, `order`, `firstlink`, `nolink`, `noref`, `xpath`, `indent`,
`max_items`, `offline`, `force`, `no_meta`, plus the custom-feed rules `mode`,
`items`, `item_title`, `item_link`, `item_content`, `item_desc`, `item_time`,
`item_author`, `item_image`. Full-text fetching is off by default on HTTP and
can be enabled with `fulltext=1`.

The examples use the Docker stack's nginx port (`8088`). In development the
downloader alone listens on `1234`.

Examples:

```bash
curl 'http://localhost:8088/read?url=https://example.com/feed.xml'
curl 'http://localhost:8088/read?url=https://example.com/feed.xml&format=json&fulltext=1'
curl 'http://localhost:8088/discover?url=https://example.com/'
```

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
| Python | 3.15 (`python:3.15-slim`) |
| Django | 6.1.3 |
| PostgreSQL | 19 (`postgres:19`) |
| nginx | 1.26.x from the Debian trixie base image (not pinned) |
| Gunicorn | 27.0.1 |
| WhiteNoise | 6.12.0 |
| psycopg | 3.3.9 (`psycopg[binary]`) |
| Scrapy | 2.20.0 |
| Twisted | 26.10.0 |
| lxml | 6.1.3 |
| Redis (optional cache) | 8.1.0 |
| Docker Compose | v2 (required) |

Python packages are pinned in `requirements.txt`. The Dockerfile pins the Python
base image tag, and both compose files pin `postgres:19`. nginx comes from the
Debian package inside `python:3.15-slim` and is not pinned; pin the base image
digest if you need byte-for-byte reproducible builds.

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
sudo cp nginx/default.site-example /etc/nginx/sites-available/default
sudo service nginx reload
```

The template proxies `/` to the Django server on port 8000 (Gunicorn in
production) and `/downloader`, `/feed`, `/feed1`, `/read`, `/rss`, `/discover`
and `/api/` to the downloader on port 1234. In Docker, `frontend/start.sh`
patches nginx's listen port to `$WEB_PORT` (default `8088`), which the compose
file exposes.

The template forwards the browser `Host` header so Django's CSRF checks pass
behind the proxy. If you reach the app by anything other than
`localhost`/`127.0.0.1`, export `ALLOWED_HOSTS` (comma separated) with that name
or IP before starting Django.

## Docker

The production image is `ghcr.io/ashcoft/pol:latest`.

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

If you never want the build fallback, use the pull-only production file:

```bash
docker compose -f docker-compose.prod.yml up -d
```

It has no `build:` section and uses `pull_policy: always`, so it always pulls
the published image and fails explicitly if the registry is unavailable.

The GHCR package is private by default. Log in once with a token that has
`read:packages`:

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u <your-github-username> --password-stdin
docker compose pull
docker compose up -d
```

Set the package visibility to public in the GitHub package settings if you want
anonymous pulls.

The stack starts two services:

* `politepol` - `ghcr.io/ashcoft/pol:latest`; nginx, Gunicorn and the downloader
  in one container, running as the unprivileged `appuser`; HTTP on `WEB_PORT`
  (default `8088`)
* `dbpolitepol` - `postgres:19`, with its data in the `pol_pg` volume mounted
  at `/var/lib/postgresql`

At start, `frontend/start.sh` waits for PostgreSQL, patches nginx's listen port,
runs `migrate` and `loaddata`, then starts the downloader, nginx and Gunicorn.
`settings.py` is generated at image build and reads the environment at import.
`collectstatic` runs at image build; WhiteNoise serves `/static/`.

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
| `WEB_PORT` | `8088` | public HTTP port |
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
WEB_PORT=8088
DEBUG=False
SECRET_KEY=put-a-long-random-value-here
ALLOWED_HOSTS=feeds.example.com
CSRF_TRUSTED_ORIGINS=https://feeds.example.com
```

### Access

```bash
http://localhost:8088
```

The container's nginx speaks HTTP. Terminate TLS in front of it, for example
with a host nginx and certbot:

```nginx
location / {
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_pass http://127.0.0.1:8088;
}
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

## Tests

```bash
cp frontend/frontend/settings.py.example frontend/frontend/settings.py
pip install pytest
pytest tests/
```

CI runs `pytest -v tests/` on Python 3.15, plus linting, a Docker image build and
an import check inside the image. The tests do not need a database; the Django
tests load settings only.

## License

MIT
