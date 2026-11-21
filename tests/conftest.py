"""Local HTTP server fixtures for reader tests (real sockets, no mocks)."""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class _Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        self._handle('GET')

    def do_HEAD(self):
        self._handle('HEAD')

    def do_POST(self):
        self._handle('POST')

    def _handle(self, method):
        route = self.server.routes.get(self.path)
        if route is None:
            route = self.server.routes.get(self.path.split('?')[0])
        if route is None:
            self.send_error(404)
            return

        result = route(method, self) if callable(route) else route
        status, headers, body = result
        if isinstance(body, str):
            body = body.encode('utf-8')

        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if method != 'HEAD':
            self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def http_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
    server.routes = {}
    server.base_url = 'http://127.0.0.1:%s' % server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


RSS_FEED = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Example feed</title>
    <link>https://example.com/</link>
    <description>An example</description>
    <language>en</language>
    <item>
      <title>First post</title>
      <link>/article</link>
      <guid>post-1</guid>
      <description><![CDATA[<p>Short summary.</p>]]></description>
      <pubDate>Tue, 21 Nov 2026 10:00:00 GMT</pubDate>
      <enclosure url="https://example.com/cover.jpg" type="image/jpeg" length="123"/>
    </item>
  </channel>
</rss>
"""

ARTICLE = """<!DOCTYPE html>
<html><head><title>First post</title></head>
<body>
<nav><a href="/">Home</a> <a href="/about">About</a></nav>
<article>
  <h1>First post</h1>
  <p>This is the full article body. It contains enough words to be scored as content,
  with commas, clauses, and a few sentences so the readability heuristic keeps it.</p>
  <p>Second paragraph adds more text so the article candidate clearly wins over the
  navigation and the sidebar. It also has a relative image below.</p>
  <img src="/images/photo.jpg" loading="lazy">
</article>
<div class="sidebar">Subscribe to our newsletter</div>
<script>alert('nope')</script>
</body></html>
"""
