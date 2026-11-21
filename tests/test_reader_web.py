import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

from .conftest import RSS_FEED

APP = os.path.join(os.path.dirname(__file__), 'reader_web_app.py')


def _free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _wait_for_port(port, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(('127.0.0.1', port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError('reader web app did not start')


@pytest.fixture
def reader_server(http_server):
    http_server.routes.update({
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
        '/': (200, {'Content-Type': 'text/html'},
              '<link rel="alternate" type="application/rss+xml" href="/feed.xml">'),
    })

    port = _free_port()
    env = dict(os.environ, PYTHONPATH=os.path.dirname(os.path.dirname(__file__)))
    process = subprocess.Popen([sys.executable, APP, str(port)], cwd=os.path.dirname(APP),
                               env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        _wait_for_port(port)
        yield 'http://127.0.0.1:%s' % port
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _get(endpoint, **params):
    target = endpoint
    if params:
        target += '?' + urllib.parse.urlencode(params)
    return urllib.request.urlopen(target, timeout=10)


def test_read_returns_rss(reader_server, http_server):
    response = _get(reader_server + '/read', url=http_server.base_url + '/feed.xml')
    body = response.read().decode('utf-8')
    assert response.status == 200
    assert response.headers['Content-Type'].startswith('application/rss+xml')
    assert 'First post' in body
    assert response.headers['Access-Control-Allow-Origin'] == '*'


def test_read_supports_json(reader_server, http_server):
    response = _get(reader_server + '/read', url=http_server.base_url + '/feed.xml',
                    format='json', proxy='1')
    payload = json.loads(response.read().decode('utf-8'))
    assert payload['title'] == 'Example feed'
    assert payload['items'][0]['title'] == 'First post'


def test_read_supports_jsonp(reader_server, http_server):
    response = _get(reader_server + '/read', url=http_server.base_url + '/feed.xml',
                    callback='myCallback', proxy='1')
    body = response.read().decode('utf-8')
    assert body.startswith('myCallback({')
    assert response.headers['Content-Type'].startswith('application/javascript')


def test_discover(reader_server, http_server):
    response = _get(reader_server + '/discover', url=http_server.base_url + '/')
    payload = json.loads(response.read().decode('utf-8'))
    assert payload['feeds'][0]['url'] == http_server.base_url + '/feed.xml'


def test_find_feeds_api_get_and_post(reader_server, http_server):
    get_response = _get(reader_server + '/api/find-feeds', url=http_server.base_url + '/')
    assert json.loads(get_response.read().decode('utf-8'))['feeds']

    request = urllib.request.Request(
        reader_server + '/api/find-feeds',
        data=json.dumps({'url': http_server.base_url + '/'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=10) as post_response:
        payload = json.loads(post_response.read().decode('utf-8'))
    assert payload['feeds'][0]['url'] == http_server.base_url + '/feed.xml'


def test_feed_preview_sanitizes_summary(reader_server, http_server):
    unsafe = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0"><channel><title>Unsafe</title><link>https://example.com/</link>
    <description>d</description><item><title>Bad</title><link>https://example.com/bad</link>
    <description><![CDATA[<p>Hello</p><script>alert(1)</script>]]></description>
    </item></channel></rss>"""
    http_server.routes['/unsafe.xml'] = (
        200, {'Content-Type': 'application/rss+xml'}, unsafe)

    response = _get(reader_server + '/api/feed-preview',
                    url=http_server.base_url + '/unsafe.xml')
    payload = json.loads(response.read().decode('utf-8'))
    summary = payload['items'][0]['summary']
    assert 'Hello' in summary
    assert '<script' not in summary


def test_feed_preview(reader_server, http_server):
    response = _get(reader_server + '/api/feed-preview',
                    url=http_server.base_url + '/feed.xml')
    payload = json.loads(response.read().decode('utf-8'))
    assert payload['title'] == 'Example feed'
    assert payload['items'][0]['link'] == http_server.base_url + '/article'


def test_missing_url_is_400(reader_server):
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _get(reader_server + '/read')
    assert excinfo.value.code == 400
    assert 'URL is required' in excinfo.value.read().decode('utf-8')


def test_invalid_url_is_400(reader_server):
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _get(reader_server + '/read', url='mailto:x@example.com')
    assert excinfo.value.code == 400


def test_upstream_failure_is_502(reader_server, http_server):
    http_server.routes['/missing'] = (404, {'Content-Type': 'text/plain'}, 'nope')
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _get(reader_server + '/read', url=http_server.base_url + '/missing')
    assert excinfo.value.code == 502


def test_invalid_format_is_400(reader_server, http_server):
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _get(reader_server + '/read', url=http_server.base_url + '/feed.xml',
             format='yaml', proxy='1')
    assert excinfo.value.code == 400


def test_options_preflight(reader_server):
    request = urllib.request.Request(reader_server + '/api/find-feeds', method='OPTIONS')
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 204
        assert response.headers['Access-Control-Allow-Origin'] == '*'


def test_feed_preview_uses_content_when_summary_is_missing(reader_server, http_server):
    feed = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel><title>Content only</title><link>https://example.com/</link>
    <description>d</description><item><title>Only</title><link>https://example.com/only</link>
    <content:encoded><![CDATA[<p>Only content</p>]]></content:encoded>
    </item></channel></rss>"""
    http_server.routes['/content-only.xml'] = (
        200, {'Content-Type': 'application/rss+xml'}, feed)

    response = _get(reader_server + '/api/feed-preview',
                    url=http_server.base_url + '/content-only.xml')
    payload = json.loads(response.read().decode('utf-8'))
    assert 'Only content' in payload['items'][0]['summary']
