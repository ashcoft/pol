import gzip
import zlib

import pytest

from pol.reader.errors import FetchError
from pol.reader.http import Fetcher

from .conftest import RSS_FEED


def test_fetch_follows_http_redirects(http_server):
    http_server.routes.update({
        '/old': (302, {'Location': '/new'}, ''),
        '/new': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
    })
    response = Fetcher(timeout=5).fetch(http_server.base_url + '/old')
    assert response.ok
    assert response.url == http_server.base_url + '/new'
    assert response.is_feed


def test_fetch_decompresses_gzip(http_server):
    http_server.routes['/gzip.xml'] = (
        200, {'Content-Type': 'application/rss+xml', 'Content-Encoding': 'gzip'},
        gzip.compress(RSS_FEED.encode()))
    response = Fetcher(timeout=5).fetch(http_server.base_url + '/gzip.xml')
    assert b'Example feed' in response.body


def test_fetch_decompresses_deflate(http_server):
    http_server.routes['/deflate.xml'] = (
        200, {'Content-Type': 'application/rss+xml', 'Content-Encoding': 'deflate'},
        zlib.compress(RSS_FEED.encode()))
    response = Fetcher(timeout=5).fetch(http_server.base_url + '/deflate.xml')
    assert b'Example feed' in response.body


def test_fetch_follows_meta_refresh(http_server):
    http_server.routes.update({
        '/refresh': (200, {'Content-Type': 'text/html'},
                     '<html><head><meta http-equiv="refresh" content="0; url=/feed.xml">'
                     '</head><body>Redirecting</body></html>'),
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
    })
    response = Fetcher(timeout=5).fetch(http_server.base_url + '/refresh')
    assert response.url == http_server.base_url + '/feed.xml'
    assert response.is_feed


def test_fetch_can_disable_meta_refresh(http_server):
    http_server.routes.update({
        '/refresh': (200, {'Content-Type': 'text/html'},
                     '<meta http-equiv="refresh" content="0; url=/feed.xml">'),
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
    })
    response = Fetcher(timeout=5).fetch(http_server.base_url + '/refresh', allow_meta=False)
    assert response.url.endswith('/refresh')


def test_fetch_enforces_size_limit(http_server):
    http_server.routes['/big'] = (200, {'Content-Type': 'text/plain'}, 'x' * 1000)
    with pytest.raises(FetchError):
        Fetcher(timeout=5, max_size=10).fetch(http_server.base_url + '/big')


def test_fetch_decodes_declared_charset(http_server):
    body = '<html><body>café</body></html>'.encode('cp1252')
    http_server.routes['/latin'] = (
        200, {'Content-Type': 'text/html; charset=windows-1252'}, body)
    response = Fetcher(timeout=5).fetch(http_server.base_url + '/latin')
    assert 'café' in response.text


def test_fetch_sends_reader_headers(http_server):
    seen = {}

    def route(method, handler):
        seen['user-agent'] = handler.headers.get('User-Agent')
        seen['accept-encoding'] = handler.headers.get('Accept-Encoding')
        return 200, {'Content-Type': 'application/rss+xml'}, RSS_FEED

    http_server.routes['/headers.xml'] = route
    Fetcher(user_agent='pol-test/1', timeout=5).fetch(http_server.base_url + '/headers.xml')
    assert seen['user-agent'] == 'pol-test/1'
    assert 'gzip' in seen['accept-encoding']


def test_fetch_http_error_is_returned_not_raised(http_server):
    http_server.routes['/missing'] = (404, {'Content-Type': 'text/plain'}, 'nope')
    response = Fetcher(timeout=5).fetch(http_server.base_url + '/missing')
    assert response.status == 404
    assert not response.ok


def test_fetch_connection_error_raises():
    with pytest.raises(FetchError):
        Fetcher(timeout=0.5).fetch('http://127.0.0.1:1/never')
