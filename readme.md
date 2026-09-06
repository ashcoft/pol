# [RSSPol](https://feed.dony.me "RSS Feed Generator")

RSS feed generator website with user friendly interface.

![PolitePaul](frontend/frontend/assets/frontend/images/apple-touch-icon-144x144-precomposed.png "PolitePaul")

Source code of an RSS feed generator website with a user friendly interface: enter a page URL, pick the elements that make up a feed, and get a ready-to-use RSS feed. A live deployment is available at [feed.dony.me](https://feed.dony.me).

## Repository layout

```
pol/                       downloader core (Twisted-based HTTP server, feed builder, client, db helpers, log, GC monitor)
frontend/                  Django app (models, views, templates, forms, migrations, fixtures, settings.py.example)
frontend/frontend/assets/ static assets (LESS/SASS, CSS, JS, images)
nginx/                     nginx site template (proxies / to Django and /downloader, /feed, /feed1 to the downloader server)
tests/                     pytest test suite
.github/workflows/        CI, release (semantic-release), Snyk security, Pullfrog
requirements.txt           Python dependencies (root-level)
Dockerfile, docker-compose.yaml, wait-for-it.sh, downloader.py
```

## Requirements

* Python 3.10+ (3.11 recommended, used by CI and Docker)
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

The template proxies `/` to the Django dev server (port 8000) and `/downloader`, `/feed`, `/feed1` to the downloader server(port 1234). In Docker, `frontend/start.sh` patches nginx's listen port to `$WEB_PORT` (default `8088`), which the compose file exposes.

## Docker

```bash
git clone https://github.com/ashcoft/pol.git
cd pol
docker compose up -d --build   # or: docker-compose up -d --build
```

The stack starts two services:

* `politepol` -the app container (built from the Dockerfile): `frontend/start.sh` starts nginx, Django, and the downloader; serves HTTP on port `8088`
* `dbpolitepol` - MySQL 5.7 with a persisted volume in `./mysql`

`wait-for-it.sh` waits for MySQL to be ready, then `frontend/start.sh` patches `settings.py` from environment variables, starts nginx, migrates the database, loads `fields.json`, and starts both the downloader and the Django server.

Useful compose environment variables: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `WEB_PORT`, `TIME_ZONE`.

### Access (port 8088)

Open the Docker host IP in a browser, e.g.:

```
http://localhost:8088
http://192.168.0.10:8088
```

## Tests

```bash
cp frontend/frontend/settings.py.example frontend/frontend/settings.py
pytest tests/
```

CI runs the same tests, pivoting checks, and a Docker image build on every push/PR. Releases are cut automatically by the Release workflow(python-semantic-release) when CI passes on `master`.

## License

MIT
