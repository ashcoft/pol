import os

import pytest

from pol.reader.cache import (
    BaseCache,
    DiskCache,
    FallbackCache,
    HttpCache,
    MemoryCache,
    NullCache,
    RedisCache,
    make_cache,
)
from pol.reader.http import Fetcher

from .conftest import RSS_FEED


def test_memory_cache_lru_eviction():
    cache = MemoryCache(max_entries=2)
    cache.set('a', 1)
    cache.set('b', 2)
    assert cache.get('a') == 1  # move a to the most recent position
    cache.set('c', 3)
    assert cache.get('b') is None
    assert cache.get('a') == 1
    assert cache.get('c') == 3


def test_memory_cache_ttl():
    cache = MemoryCache()
    cache.set('a', 1, ttl=-1)
    assert cache.get('a') is None


def test_null_cache_stores_nothing():
    cache = NullCache()
    cache.set('a', 1)
    assert cache.get('a') is None


def test_disk_cache_roundtrip_and_ttl(tmp_path):
    cache = DiskCache(str(tmp_path))
    cache.set('key', {'value': 42})
    assert cache.get('key') == {'value': 42}
    cache.set('expired', 1, ttl=-1)
    assert cache.get('expired') is None
    cache.clear()
    assert cache.get('key') is None


def test_make_cache_backends(tmp_path):
    assert isinstance(make_cache('memory'), MemoryCache)
    assert isinstance(make_cache('none'), NullCache)
    assert isinstance(make_cache('diskcache', directory=str(tmp_path)), DiskCache)
    # Unknown names fall back to memory rather than breaking the caller.
    assert isinstance(make_cache('nonsense'), MemoryCache)


def test_redis_cache_optional():
    pytest.importorskip('redis')
    url = os.environ.get('POL_TEST_REDIS_URL', 'redis://127.0.0.1:6379/15')
    try:
        cache = RedisCache(url)
        cache._client.ping()
    except Exception:
        pytest.skip('redis is not running')
    cache.set('reader-test', {'a': 1}, ttl=5)
    assert cache.get('reader-test') == {'a': 1}
    cache.delete('reader-test')
    assert cache.get('reader-test') is None


def test_http_cache_conditional_headers():
    cache = HttpCache(MemoryCache(), ttl=60)
    cache.store('https://example.com/f', 200,
                {'etag': '"v1"', 'last-modified': 'Tue, 21 Nov 2026 10:00:00 GMT'},
                b'body')
    assert cache.conditional_headers('https://example.com/f') == {
        'If-None-Match': '"v1"',
        'If-Modified-Since': 'Tue, 21 Nov 2026 10:00:00 GMT',
    }


def test_fetcher_revalidates_with_etag(http_server):
    state = {'count': 0}

    def route(method, handler):
        state['count'] += 1
        if handler.headers.get('If-None-Match') == '"v1"':
            return 304, {'ETag': '"v1"'}, b''
        return 200, {'Content-Type': 'application/rss+xml', 'ETag': '"v1"'}, RSS_FEED

    http_server.routes['/feed.xml'] = route
    cache = HttpCache(MemoryCache(), ttl=60)
    fetcher = Fetcher(timeout=5, cache=cache)

    first = fetcher.fetch(http_server.base_url + '/feed.xml')
    second = fetcher.fetch(http_server.base_url + '/feed.xml')

    assert first.body == second.body
    assert second.status == 200
    assert state['count'] == 2


def test_fetcher_cache_only_skips_network(http_server):
    http_server.routes['/feed.xml'] = (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED)
    cache = HttpCache(MemoryCache(), ttl=60)
    fetcher = Fetcher(timeout=5, cache=cache)
    fetcher.fetch(http_server.base_url + '/feed.xml')

    offline = Fetcher(timeout=5, cache=cache, cache_only=True)
    assert offline.fetch(http_server.base_url + '/feed.xml').body == RSS_FEED.encode()

    with pytest.raises(Exception):
        offline.fetch(http_server.base_url + '/missing.xml')


class _FailingCache(BaseCache):
    def get(self, key, default=None):
        raise ConnectionError('backend down')

    def set(self, key, value, ttl=None):
        raise ConnectionError('backend down')

    def delete(self, key):
        raise ConnectionError('backend down')

    def clear(self):
        raise ConnectionError('backend down')


def test_fallback_cache_switches_to_memory():
    cache = FallbackCache(_FailingCache(), MemoryCache())
    cache.set('a', 1)
    assert cache.get('a') == 1


def test_make_cache_redis_unavailable_falls_back():
    pytest.importorskip('redis')
    cache = make_cache('redis', url='redis://127.0.0.1:1/0')
    cache.set('a', 1)
    assert cache.get('a') == 1


def test_disk_cache_roundtrips_bytes(tmp_path):
    cache = DiskCache(str(tmp_path))
    cache.set('body', {'body': b'\x00\xff\x01', 'status': 200})
    assert cache.get('body') == {'body': b'\x00\xff\x01', 'status': 200}


def test_file_cache_enforces_a_byte_budget(tmp_path):
    from pol.reader.cache import _FileCache

    cache = _FileCache(str(tmp_path), max_entries=100, max_bytes=2048)
    for index in range(20):
        cache.set('key-%d' % index, {'body': b'x' * 512})

    total = sum(entry.stat().st_size for entry in os.scandir(str(tmp_path))
                if entry.name.endswith('.cache'))
    assert total <= 2048
