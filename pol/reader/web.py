"""Twisted endpoints exposing the reader over HTTP.

Routes are handled by the downloader server:

``GET  /read``               read a feed (or discover one) and return a feed
``GET  /discover``           list feeds found on a page (rss-finder JSON shape)
``GET  /api/find-feeds``     same as /discover, rss-finder compatible
``POST /api/find-feeds``     JSON ``{"url": "..."}`` body
``GET  /api/feed-preview``   parsed feed preview as JSON
"""

from __future__ import annotations

import json
import sys
from urllib.parse import parse_qs

from twisted.internet import threads
from twisted.web.server import NOT_DONE_YET

from .cache import HttpCache, make_cache
from .errors import FetchError, InvalidURLError, ParseError
from .http import DEFAULT_MAX_SIZE, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT, Fetcher
from .parse import html_to_text, sanitize_html
from .pipeline import Options, discover, process

_PATHS = frozenset({
    b'/read', b'/rss', b'/discover', b'/api/find-feeds', b'/api/feed-preview',
    b'/api/read',
})
_API_PATHS = frozenset({b'/discover', b'/api/find-feeds', b'/api/feed-preview'})


def _arg(request, name, default=None):
    values = request.args.get(name.encode('ascii'))
    if not values:
        return default
    return values[0].decode('utf-8', 'replace')


def _flag(request, name, default=False):
    value = _arg(request, name)
    if value is None:
        return default
    return value.strip().lower() in ('', '1', 'true', 'yes', 'on', 'y')


def _int_arg(request, name, default):
    try:
        return int(_arg(request, name, default))
    except (TypeError, ValueError):
        return default


def _effective_allow_private(endpoints, options):
    # Never taken from the request: an unauthenticated caller must not be able to reach
    # private services. Only the operator's setting counts.
    if endpoints.allow_private is not None:
        return endpoints.allow_private
    if endpoints.block_private_hosts is not None:
        return not endpoints.block_private_hosts
    return None


class ReaderEndpoints:
    def __init__(self, user_agent, cache_backend='memory', cache_dir=None,
                 cache_ttl=3600, redis_url=None, timeout=DEFAULT_TIMEOUT,
                 max_size=DEFAULT_MAX_SIZE, verify_ssl=True,
                 allow_private=None, block_private_hosts=True):
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.timeout = timeout
        self.max_size = max_size
        self.verify_ssl = verify_ssl
        self.allow_private = allow_private
        self.block_private_hosts = block_private_hosts
        store = make_cache(cache_backend, directory=cache_dir, url=redis_url)
        self.http_cache = HttpCache(store, ttl=cache_ttl)

    def handles(self, path):
        return path in _PATHS

    def _fetcher(self, options):
        return Fetcher(
            user_agent=options.user_agent,
            timeout=options.timeout,
            max_size=options.max_size,
            cache=self.http_cache,
            verify_ssl=self.verify_ssl,
            allow_meta_refresh=options.follow_meta,
            cache_only=options.cache_only,
            allow_private=_effective_allow_private(self, options),
        )

    def _options(self, request):
        callback = _arg(request, 'callback')
        fmt = _arg(request, 'format', 'rss')
        if callback:
            fmt = 'jsonp'
        return Options(
            format=fmt,
            callback=callback,
            fulltext=_flag(request, 'fulltext') or _flag(request, 'fill'),
            proxy=_flag(request, 'proxy'),
            clip=_flag(request, 'clip'),
            resolve=_flag(request, 'resolve'),
            search=_arg(request, 'search'),
            xpath=_arg(request, 'xpath'),
            items=_arg(request, 'items'),
            item_link=_arg(request, 'item_link'),
            item_title=_arg(request, 'item_title'),
            item_content=_arg(request, 'item_content'),
            item_time=_arg(request, 'item_time'),
            item_desc=_arg(request, 'item_desc'),
            item_author=_arg(request, 'item_author'),
            item_image=_arg(request, 'item_image'),
            mode=_arg(request, 'mode'),
            max_items=max(0, min(_int_arg(request, 'max_items', 20), 200)),
            indent=_flag(request, 'indent'),
            cache=True,
            cache_only=_flag(request, 'offline') or _flag(request, 'cache_only'),
            force=_flag(request, 'force'),
            timeout=self.timeout,
            max_size=self.max_size,
            user_agent=self.user_agent,
            verify_ssl=self.verify_ssl,
            follow_meta=not _flag(request, 'no_meta'),
        )

    def get(self, request):
        if request.path == b'/api/feed-preview':
            return self._preview(request)
        if request.path in (b'/discover', b'/api/find-feeds'):
            return self._discover(request, _arg(request, 'url'))
        return self._read(request, _arg(request, 'url') or _arg(request, 'feed'))

    def post(self, request):
        if request.path not in (b'/api/find-feeds', b'/read', b'/rss', b'/api/read'):
            return self._error(request, 404, 'Not found', json_body=True)
        url = _arg(request, 'url')
        if not url:
            url = self._body_url(request)
        if request.path == b'/api/find-feeds':
            return self._discover(request, url)
        return self._read(request, url)

    def options(self, request):
        self._cors(request)
        request.setResponseCode(204)
        request.finish()
        return NOT_DONE_YET

    @staticmethod
    def _body_url(request):
        try:
            body = request.content.read()
        except Exception:
            return None
        if not body:
            return None
        try:
            data = json.loads(body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            data = {key: values[0].decode('utf-8', 'replace')
                    for key, values in parse_qs(body.decode('utf-8', 'replace')).items()}
        if isinstance(data, dict):
            return data.get('url')
        return None

    def _read(self, request, url):
        if not url:
            return self._error(request, 400, 'URL is required',
                               json_body=request.path in _API_PATHS)
        options = self._options(request)
        fetcher = self._fetcher(options)

        def work():
            return process(url, options=options, fetcher=fetcher)

        deferred = threads.deferToThread(work)
        deferred.addCallback(lambda result: self._write(
            request, result.text.encode('utf-8'), result.content_type))
        deferred.addErrback(lambda failure: self._fail(
            request, failure, json_body=request.path in _API_PATHS))
        return NOT_DONE_YET

    def _discover(self, request, url):
        if not url:
            return self._error(request, 400, 'URL is required', json_body=True)
        options = self._options(request)
        fetcher = self._fetcher(options)

        def work():
            return discover(url, options=options, fetcher=fetcher)

        deferred = threads.deferToThread(work)
        deferred.addCallback(lambda refs: self._write(
            request,
            json.dumps({'feeds': [ref.as_dict() for ref in refs]},
                       ensure_ascii=False).encode('utf-8'),
            'application/json; charset=utf-8'))
        deferred.addErrback(lambda failure: self._fail(request, failure, json_body=True))
        return NOT_DONE_YET

    def _preview(self, request):
        url = _arg(request, 'url')
        if not url:
            return self._error(request, 400, 'URL is required', json_body=True)
        options = self._options(request)
        options.fulltext = False
        options.proxy = True
        options.format = 'json'
        fetcher = self._fetcher(options)

        def work():
            return process(url, options=options, fetcher=fetcher).feed

        def render(feed):
            payload = {
                'title': feed.title,
                'link': feed.link,
                'description': feed.description,
                'url': feed.url,
                'items': [
                    {
                        'title': item.title,
                        'link': item.link,
                        'date': item.date.isoformat() if item.date else None,
                        'summary': sanitize_html(item.summary or item.content),
                        'summary_text': html_to_text(item.summary or item.content),
                        'image': item.images[0] if item.images else None,
                    }
                    for item in feed.items[:50]
                ],
            }
            return self._write(request, json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                               'application/json; charset=utf-8')

        deferred = threads.deferToThread(work)
        deferred.addCallback(render)
        deferred.addErrback(lambda failure: self._fail(request, failure, json_body=True))
        return NOT_DONE_YET

    def _write(self, request, body, content_type):
        try:
            self._cors(request)
            request.setHeader(b'Content-Type', content_type.encode('ascii'))
            request.setHeader(b'Cache-Control', b'public, max-age=300')
            request.write(body)
            request.finish()
        except Exception as exc:  # client disconnected mid-response
            sys.stderr.write('Reader response error: %s\n' % exc)
        return None

    def _cors(self, request):
        request.setHeader(b'Access-Control-Allow-Origin', b'*')
        request.setHeader(b'Access-Control-Allow-Methods', b'GET, POST, OPTIONS')
        request.setHeader(b'Access-Control-Allow-Headers', b'Content-Type')

    def _fail(self, request, failure, json_body=False):
        error = failure.value if hasattr(failure, 'value') else failure
        if isinstance(error, InvalidURLError):
            status, message = 400, str(error)
        elif isinstance(error, FetchError):
            status, message = 502, str(error)
        elif isinstance(error, ParseError):
            status, message = 422, str(error)
        elif isinstance(error, ValueError):
            status, message = 400, str(error)
        else:
            status, message = 500, 'Reader error'
            sys.stderr.write('Reader error: %s\n' % (failure.getTraceback()
                                                     if hasattr(failure, 'getTraceback') else error))
        return self._error(request, status, message, json_body=json_body)

    def _error(self, request, status, message, json_body=False):
        try:
            self._cors(request)
            request.setResponseCode(status)
            if json_body:
                body = json.dumps({'error': message}, ensure_ascii=False).encode('utf-8')
                request.setHeader(b'Content-Type', b'application/json; charset=utf-8')
            else:
                body = (message + '\n').encode('utf-8')
                request.setHeader(b'Content-Type', b'text/plain; charset=utf-8')
            request.write(body)
            request.finish()
        except Exception:
            return NOT_DONE_YET
        return NOT_DONE_YET
