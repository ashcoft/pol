import sys

import settings as pol_settings
from pol.server import Server
from pol.reader.web import ReaderEndpoints
from settings import DATABASES, SNAPSHOT_DIR, DOWNLOADER_USER_AGENT, DEBUG


port = sys.argv[1] if len(sys.argv) >= 2 else 1234

reader = ReaderEndpoints(
    DOWNLOADER_USER_AGENT,
    cache_backend=getattr(pol_settings, 'CACHE_BACKEND', 'memory'),
    cache_dir=getattr(pol_settings, 'CACHE_DIR', None),
    cache_ttl=getattr(pol_settings, 'CACHE_TTL', 3600),
    redis_url=getattr(pol_settings, 'REDIS_URL', None),
    timeout=getattr(pol_settings, 'READER_TIMEOUT', 20),
    max_size=getattr(pol_settings, 'READER_MAX_SIZE', 8 * 1024 * 1024),
    verify_ssl=getattr(pol_settings, 'READER_VERIFY_SSL', True),
    allow_private=True if getattr(pol_settings, 'READER_ALLOW_PRIVATE', False) else None,
)

Server(port, DATABASES['default'], SNAPSHOT_DIR, DOWNLOADER_USER_AGENT,
       reader=reader).run()
