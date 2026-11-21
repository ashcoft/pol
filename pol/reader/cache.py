"""Cache backends and the HTTP response cache built on top of them.

Backends: in-process memory (always available), redis and diskcache. Redis and
diskcache are optional dependencies; when they are missing or unusable the
factory falls back to the memory backend instead of breaking the caller.
"""

from __future__ import annotations

import hashlib
import os
import pickle
import tempfile
import threading
import time
from collections import OrderedDict


class BaseCache:
    def get(self, key, default=None):
        raise NotImplementedError

    def set(self, key, value, ttl=None):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError


class NullCache(BaseCache):
    """Backend that stores nothing, used when caching is disabled."""

    def get(self, key, default=None):
        return default

    def set(self, key, value, ttl=None):
        return None

    def delete(self, key):
        return None

    def clear(self):
        return None


class MemoryCache(BaseCache):
    """LRU cache with optional per-entry expiry, safe across threads."""

    def __init__(self, max_entries=512):
        self.max_entries = max(1, int(max_entries))
        self._data = OrderedDict()
        self._lock = threading.RLock()

    def _alive(self, entry):
        expires, _value = entry
        return expires is None or expires > time.time()

    def get(self, key, default=None):
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return default
            if not self._alive(entry):
                del self._data[key]
                return default
            self._data.move_to_end(key)
            return entry[1]

    def set(self, key, value, ttl=None):
        expires = time.time() + ttl if ttl else None
        with self._lock:
            self._data[key] = (expires, value)
            self._data.move_to_end(key)
            while len(self._data) > self.max_entries:
                self._data.popitem(last=False)

    def delete(self, key):
        with self._lock:
            self._data.pop(key, None)

    def clear(self):
        with self._lock:
            self._data.clear()


class _FileCache(BaseCache):
    """Minimal pickle-on-disk backend used when diskcache is unavailable."""

    def __init__(self, directory, max_entries=10000):
        self.directory = os.path.abspath(directory)
        self.max_entries = max(1, int(max_entries))
        self._lock = threading.RLock()
        os.makedirs(self.directory, exist_ok=True)

    def _path(self, key):
        digest = hashlib.sha256(str(key).encode('utf-8')).hexdigest()
        return os.path.join(self.directory, digest + '.cache')

    def get(self, key, default=None):
        path = self._path(key)
        try:
            with open(path, 'rb') as handle:
                payload = pickle.load(handle)
        except (OSError, pickle.PickleError, EOFError, AttributeError,
                ImportError, ValueError, TypeError):
            return default
        expires = payload.get('expires')
        if expires is not None and expires <= time.time():
            self.delete(key)
            return default
        return payload.get('value', default)

    def set(self, key, value, ttl=None):
        payload = {'expires': time.time() + ttl if ttl else None, 'value': value}
        path = self._path(key)
        with self._lock:
            fd, tmp = tempfile.mkstemp(dir=self.directory, suffix='.tmp')
            try:
                with os.fdopen(fd, 'wb') as handle:
                    pickle.dump(payload, handle, pickle.HIGHEST_PROTOCOL)
                os.replace(tmp, path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            self._evict()

    def _evict(self):
        try:
            entries = [entry for entry in os.scandir(self.directory)
                       if entry.name.endswith('.cache')]
        except OSError:
            return
        excess = len(entries) - self.max_entries
        if excess <= 0:
            return
        try:
            entries.sort(key=lambda entry: entry.stat().st_mtime)
        except OSError:
            return
        for entry in entries[:excess]:
            try:
                os.unlink(entry.path)
            except OSError:
                pass

    def delete(self, key):
        try:
            os.unlink(self._path(key))
        except OSError:
            pass

    def clear(self):
        try:
            for entry in os.scandir(self.directory):
                if entry.name.endswith('.cache'):
                    os.unlink(entry.path)
        except OSError:
            pass


class DiskCache(BaseCache):
    """diskcache backend, falling back to a small stdlib file cache."""

    def __init__(self, directory, max_entries=10000):
        try:
            import diskcache
        except ImportError:
            self._backend = _FileCache(directory, max_entries=max_entries)
            self._uses_expire_kwarg = False
        else:
            self._backend = diskcache.Cache(
                directory, eviction_policy='least-frequently-used',
                size_limit=256 * 1024 * 1024)
            self._uses_expire_kwarg = True

    def get(self, key, default=None):
        return self._backend.get(key, default)

    def set(self, key, value, ttl=None):
        if self._uses_expire_kwarg:
            self._backend.set(key, value, expire=ttl)
        else:
            self._backend.set(key, value, ttl=ttl)

    def delete(self, key):
        self._backend.delete(key)

    def clear(self):
        self._backend.clear()


class RedisCache(BaseCache):
    def __init__(self, url='redis://127.0.0.1:6379/0', prefix='pol:'):
        import redis

        self._client = redis.Redis.from_url(url)
        self._prefix = prefix

    def _key(self, key):
        return self._prefix + str(key)

    def get(self, key, default=None):
        raw = self._client.get(self._key(key))
        if raw is None:
            return default
        try:
            return pickle.loads(raw)
        except (pickle.PickleError, EOFError):
            return default

    def set(self, key, value, ttl=None):
        self._client.set(self._key(key), pickle.dumps(value, pickle.HIGHEST_PROTOCOL),
                         ex=int(ttl) if ttl else None)

    def delete(self, key):
        self._client.delete(self._key(key))

    def clear(self):
        for key in self._client.scan_iter(self._prefix + '*'):
            self._client.delete(key)


def make_cache(backend=None, **kwargs):
    """Build a cache backend by name.

    Accepted names: ``memory`` (default), ``redis``, ``diskcache``/``disk`` and
    ``none``. Unknown names and unavailable optional dependencies fall back to
    memory so a misconfigured deployment still serves feeds.
    """
    backend = (backend or os.environ.get('POL_CACHE_BACKEND')
               or os.environ.get('CACHE') or 'memory').strip().lower()

    if backend in ('none', 'off', 'null'):
        return NullCache()
    if backend in ('diskcache', 'disk', 'file'):
        directory = kwargs.get('directory') or os.environ.get(
            'DISKCACHE_DIR', os.path.join(os.path.expanduser('~'), '.cache', 'pol'))
        try:
            return DiskCache(directory, max_entries=kwargs.get('max_entries', 10000))
        except Exception:
            return MemoryCache(kwargs.get('max_entries', 512))
    if backend == 'redis':
        url = kwargs.get('url') or os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
        try:
            return RedisCache(url)
        except Exception:
            return MemoryCache(kwargs.get('max_entries', 512))
    return MemoryCache(kwargs.get('max_entries', 512))


class HttpCache:
    """Store fetched responses and expose conditional-request headers."""

    def __init__(self, cache, ttl=3600, prefix='http:'):
        self.cache = cache
        self.ttl = ttl
        self.prefix = prefix

    def _key(self, url):
        return self.prefix + url

    def get(self, url):
        entry = self.cache.get(self._key(url))
        if not isinstance(entry, dict):
            return None
        return entry

    def conditional_headers(self, url):
        entry = self.get(url)
        if not entry:
            return {}
        headers = {}
        if entry.get('etag'):
            headers['If-None-Match'] = entry['etag']
        if entry.get('last_modified'):
            headers['If-Modified-Since'] = entry['last_modified']
        return headers

    def store(self, url, status, headers, body, final_url=None):
        stored_headers = {key: value for key, value in headers.items()
                          if key.lower() not in ('content-encoding', 'content-length')}
        entry = {
            'status': status,
            'headers': stored_headers,
            'body': body,
            'url': final_url or url,
            'etag': headers.get('etag'),
            'last_modified': headers.get('last-modified'),
        }
        self.cache.set(self._key(url), entry, ttl=self.ttl)
        return entry

    def renew(self, url):
        entry = self.get(url)
        if entry:
            self.cache.set(self._key(url), entry, ttl=self.ttl)
        return entry
