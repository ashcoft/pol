"""Cache backends and the HTTP response cache built on top of them.

Backends: in-process memory (always available), redis and a JSON-backed disk
cache. Redis is optional; when it is missing or unusable the factory falls back
to the memory backend instead of breaking the caller.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
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


def _encode_value(value):
    """Encode cache values as JSON without pickle."""
    if isinstance(value, bytes):
        return {'__bytes__': base64.b64encode(value).decode('ascii')}
    if isinstance(value, dict):
        return {str(key): _encode_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode_value(item) for item in value]
    return value


def _decode_value(value):
    if isinstance(value, dict):
        if set(value) == {'__bytes__'}:
            return base64.b64decode(value['__bytes__'])
        return {key: _decode_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode_value(item) for item in value]
    return value


class _FileCache(BaseCache):
    """Disk-backed cache using JSON-safe serialization."""

    def __init__(self, directory, max_entries=10000, max_bytes=256 * 1024 * 1024):
        self.directory = os.path.abspath(directory)
        self.max_entries = max(1, int(max_entries))
        self.max_bytes = max(1, int(max_bytes))
        self._lock = threading.RLock()
        os.makedirs(self.directory, exist_ok=True)

    def _path(self, key):
        digest = hashlib.sha256(str(key).encode('utf-8')).hexdigest()
        return os.path.join(self.directory, digest + '.cache')

    def get(self, key, default=None):
        path = self._path(key)
        try:
            with open(path, encoding='utf-8') as handle:
                payload = json.load(handle)
        except (OSError, ValueError, TypeError):
            return default
        expires = payload.get('expires')
        if expires is not None and expires <= time.time():
            self.delete(key)
            return default
        try:
            return _decode_value(payload.get('value'))
        except (ValueError, TypeError):
            return default

    def set(self, key, value, ttl=None):
        payload = {'expires': time.time() + ttl if ttl else None,
                   'value': _encode_value(value)}
        path = self._path(key)
        with self._lock:
            fd, tmp = tempfile.mkstemp(dir=self.directory, suffix='.tmp')
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                    json.dump(payload, handle, ensure_ascii=False)
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
        try:
            entries.sort(key=lambda entry: entry.stat().st_mtime)
            sizes = [entry.stat().st_size for entry in entries]
        except OSError:
            return
        excess = len(entries) - self.max_entries
        total = sum(sizes)
        while entries and (excess > 0 or total > self.max_bytes):
            entry = entries.pop(0)
            size = sizes.pop(0)
            try:
                os.unlink(entry.path)
            except OSError:
                continue
            total -= size
            excess -= 1

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


class DiskCache(_FileCache):
    """Disk-backed cache with TTL and a bounded number of entries."""


class FallbackCache(BaseCache):
    """Use a primary backend until it fails, then switch to memory."""

    def __init__(self, primary, fallback=None):
        self.primary = primary
        self.fallback = fallback or MemoryCache()
        self._primary_ok = True

    def _disable(self):
        self._primary_ok = False

    def get(self, key, default=None):
        if self._primary_ok:
            try:
                return self.primary.get(key, default)
            except Exception:
                self._disable()
        return self.fallback.get(key, default)

    def set(self, key, value, ttl=None):
        if self._primary_ok:
            try:
                self.primary.set(key, value, ttl=ttl)
                return
            except Exception:
                self._disable()
        self.fallback.set(key, value, ttl=ttl)

    def delete(self, key):
        if self._primary_ok:
            try:
                self.primary.delete(key)
                return
            except Exception:
                self._disable()
        self.fallback.delete(key)

    def clear(self):
        if self._primary_ok:
            try:
                self.primary.clear()
                return
            except Exception:
                self._disable()
        self.fallback.clear()


class RedisCache(BaseCache):
    def __init__(self, url='redis://127.0.0.1:6379/0', prefix='pol:v2:'):
        import redis

        self._client = redis.Redis.from_url(
            url, socket_connect_timeout=1, socket_timeout=1)
        self._prefix = prefix

    def ping(self):
        self._client.ping()

    def _key(self, key):
        return self._prefix + str(key)

    def get(self, key, default=None):
        raw = self._client.get(self._key(key))
        if raw is None:
            return default
        try:
            return _decode_value(json.loads(raw.decode('utf-8')))
        except (ValueError, UnicodeDecodeError, TypeError):
            return default

    def set(self, key, value, ttl=None):
        payload = json.dumps(_encode_value(value), ensure_ascii=False).encode('utf-8')
        self._client.set(self._key(key), payload, ex=int(ttl) if ttl else None)

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
        fallback = MemoryCache(kwargs.get('max_entries', 512))
        try:
            cache = RedisCache(url)
            cache.ping()
            return FallbackCache(cache, fallback)
        except Exception:
            return fallback
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
