# [RSSPol](https://feed.dony.me "RSS Feed Generator")

RSS feed generator website with user friendly interface.

![PolitePaul](frontend/frontend/assets/frontend/images/apple-touch-icon-144x144-precomposed.png "PolitePaul")

Source code of an RSS feed generator website with a user friendly interface: enter a page URL, pick the elements that make up a feed, and get a ready-to-use RSS feed. A live deployment is available at [feed.dony.me](https://feed.dony.me).

## Repository layout

```
pol/                       downloader core (Twisted-based HTTP server, feed builder, client, db helpers, log, GC monitor)
pol/reader/                feed reader: discovery, parsing, full text, caches, output formats, CLI
frontend/                  Django app (models, views, templates, forms, migrations, fixtures, settings.py.example)
frontend/frontend/assets/ static assets (LESS/SASS, CSS, JS, images)
nginx/                     nginx site template (proxies / to Django and /downloader, /feed, /feed1, /read, /discover, /api to the downloader server)
tests/                     pytest test suite
.github/workflows/        CI, release (semantic-release), Snyk security, Pullfrog
requirements.txt           Python dependencies (root-level)
Dockerfile, docker-compose.yaml, wait-for-it.sh, downloader.py
```

## Feed reader features

Besides scraping a page into a new feed, pol can read, enrich and re-export
existing feeds:

* Read RSS 0.9x/2.0, Atom 0.3/1.0, RDF (RSS 1.0) and JSON Feed 1.0/1.1.
* Discover feeds on a page, ported from [ashcoft/rss-finder](https://github.com/ashcoft/rss-finder):
  `<link rel="alternate">`, feed-looking anchors, well-known paths, then every
  candidate is verified by parsing it.
* Fetch the full article text for feed items (readability-style extraction,
  or a manual XPath).
* Build feeds from JSON, HTML or XML documents with hand-written rules.
* Export as RSS 2.0, JSON Feed, CSV, HTML or JSONP.
* HTTP caching with memory, redis or diskcache backends and
  `ETag`/`Last-Modified` revalidation.
* Replace tracking links with direct links, including known redirect wrappers
  (`l.facebook.com`, `google.com/url`, `out.reddit.com`, ...).
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
`resolve`, `search`, `xpath`, `indent`, `max_items`, `offline`, `force`,
`no_meta`, plus the custom-feed rules `mode`, `items`, `item_title`,
`item_link`, `item_content`, `item_desc`, `item_time`, `item_author`,
`item_image`. Full-text fetching is off by default on HTTP and can be enabled
with `fulltext=1`.

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

## Cache backends

Set `POL_CACHE_BACKEND` (or `CACHE_BACKEND` in `settings.py`) to `memory`
(default), `diskcache`, `redis` or `none`. The `diskcache` backend is a built-in
JSON-backed disk cache; `POL_CACHE_DIR` selects its directory. `POL_REDIS_URL`
selects the redis server. The reader uses conditional requests
(`If-None-Match` / `If-Modified-Since`) and falls back to the memory backend
when Redis is unavailable.

## Requirements

* Python 3.12+ (3.15 recommended, used by CI and Docker)
* MySQL 5.7+ (used by both the frontend and the downloader)
* System build dependencies for `mysqlclient`, `lxml` and Scrapy, e.g. on Ubuntu/Debian:

```bash
sudo apt-get install build-essential pkg-config default-libmysqlclient-dev libxml2-dev libxslt1-dev libffi-dev libssl-dev gettext
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
pip install mysqlclient pytest
```

Create the Django settings module (the repo expects `settings.py` next to the `frontend` package; it is git-ignored):

```bash
cp frontend/frontend/settings.py.example frontend/frontend/settings.py
```

Create the database:

```bash
mysql -uroot -p -e 'CREATE DATABASE pol DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;'
```

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

For the frontend to reach the downloader (`/downloader`, `/feed`, `/feed1`), install nginx and use the included site template:

```bash
sudo apt-get install nginx
sudo cp nginx/default.site-example /etc/nginx/sites-available/default
sudo service nginx reload
```

The template proxies `/` to Gunicorn (port 8000) and `/downloader`, `/feed`, `/feed1` to the downloader server(port 1234). In Docker, `frontend/start.sh` patches nginx's listen port to `$WEB_PORT` (default `8088`), which the compose file exposes.

The template forwards the browser `Host` header so Django's CSRF checks pass behind the proxy. If you reach the app by anything other than `localhost`/`127.0.0.1`, export `ALLOWED_HOSTS` (comma separated) with that name or IP before starting Django.

## Docker

```bash
git clone https://github.com/ashcoft/pol.git
cd pol
docker compose up -d --build   # or: docker-compose up -d --build
```

The stack starts two services:

* `politepol` -the app container (built from the Dockerfile): `frontend/start.sh` starts nginx, Gunicorn (the Django WSGI app), and the downloader; serves HTTP on port `8088`
* `dbpolitepol` - MySQL 5.7 with a persisted volume in `./mysql`

`wait-for-it.sh` waits for MySQL to be ready, then `frontend/start.sh` patches `settings.py` from environment variables, starts nginx, migrates the database, loads `fields.json`, and starts both the downloader and Gunicorn.

Gunicorn is installed from `requirements.txt`, so the app no longer falls back to
the Django development server. `GUNICORN_WORKERS` (default `3`),
`GUNICORN_THREADS` (default `4`) and `GUNICORN_TIMEOUT` (default `120`) tune it.
Static files are served by WhiteNoise, and `frontend/start.sh` runs
`collectstatic` before Gunicorn starts, so `/static/` keeps working without the
Django development server.

Useful compose environment variables: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `WEB_PORT`, `TIME_ZONE`, `ALLOWED_HOSTS`, `GUNICORN_WORKERS`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`, `POL_CACHE_BACKEND`, `POL_CACHE_DIR`, `POL_REDIS_URL`, `POL_READER_TIMEOUT`, `POL_READER_MAX_SIZE`, `POL_READER_VERIFY_SSL`.

### Access (port 8088)

`ALLOWED_HOSTS` defaults to loopback, so set it to the hostname or IP you use
to reach the app (comma separated), then open it in a browser, e.g.:

```bash
ALLOWED_HOSTS=192.168.0.10 docker compose up -d
```

```
http://localhost:8088
http://192.168.0.10:8088
```

## Tests

```bash
cp frontend/frontend/settings.py.example frontend/frontend/settings.py
pytest tests/
```

CI runs the same tests, linting checks, and a Docker image build on pull requests and pushes to `main`. Releases are cut automatically by the Release workflow (python-semantic-release) when CI passes on `main`.

## License

MIT
