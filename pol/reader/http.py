"""HTTP fetching with compression, redirects, meta refresh and caching."""

from __future__ import annotations

import re
import ssl
import zlib
from dataclasses import dataclass, field
from urllib import error, request as urllib_request
from urllib.parse import urljoin

from lxml import html as lxml_html

from . import charset
from .cache import HttpCache
from .errors import FetchError
from .urls import clean_url, normalize_url

DEFAULT_USER_AGENT = 'pol-reader/1.0 (+https://github.com/ashcoft/pol)'
DEFAULT_TIMEOUT = 20
DEFAULT_MAX_SIZE = 8 * 1024 * 1024
MAX_DECOMPRESSED_SIZE = 32 * 1024 * 1024

FEED_CONTENT_TYPES = (
    'application/rss+xml', 'application/atom+xml', 'application/rdf+xml',
    'application/feed+json', 'application/xml', 'text/xml',
)
HTML_CONTENT_TYPES = ('text/html', 'application/xhtml+xml')

_META_REFRESH_RE = re.compile(
    r'url\s*=\s*[\'"]?([^\'";]+)', re.IGNORECASE)
_META_DELAY_RE = re.compile(r'^\s*(\d+)')


@dataclass
class Response:
    url: str
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b''
    encoding: str = ''

    @property
    def content_type(self) -> str:
        return self.headers.get('content-type', '').split(';')[0].strip().lower()

    @property
    def declared_charset(self) -> str:
        return charset.charset_from_content_type(self.headers.get('content-type')) or ''

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def text(self) -> str:
        if not hasattr(self, '_text'):
            self._text, self.encoding = charset.decode(self.body, self.headers.get('content-type'))
        return self._text

    @property
    def is_html(self) -> bool:
        if self.content_type in HTML_CONTENT_TYPES:
            return True
        head = self.body[:512].lstrip().lower()
        return head.startswith(b'<!doctype html') or head.startswith(b'<html')

    @property
    def is_feed(self) -> bool:
        if self.content_type in FEED_CONTENT_TYPES:
            return True
        head = self.body[:512].lstrip().lower()
        return (head.startswith(b'<?xml') or head.startswith(b'<rss')
                or head.startswith(b'<feed') or head.startswith(b'<rdf')
                or head.startswith(b'{"version"'))


class UrllibTransport:
    """Default transport. Returns (status, headers, body, final_url)."""

    def __init__(self, timeout=DEFAULT_TIMEOUT, max_size=DEFAULT_MAX_SIZE,
                 verify_ssl=True):
        self.timeout = timeout
        self.max_size = max_size
        handlers = []
        if not verify_ssl:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            handlers.append(urllib_request.HTTPSHandler(context=context))
        self._opener = urllib_request.build_opener(*handlers)

    def request(self, url, headers, data=None, method='GET', max_size=None):
        limit = max_size or self.max_size
        req = urllib_request.Request(url, data=data, headers=headers, method=method)
        try:
            response = self._opener.open(req, timeout=self.timeout)
        except error.HTTPError as exc:
            response = exc
        except (error.URLError, OSError, ValueError) as exc:
            raise FetchError('Could not fetch %s: %s' % (url, exc), url=url) from exc

        try:
            body = response.read(limit + 1)
        except OSError as exc:
            raise FetchError('Could not read %s: %s' % (url, exc), url=url) from exc
        finally:
            try:
                response.close()
            except Exception:
                pass

        if len(body) > limit:
            raise FetchError('Response is larger than %s bytes' % limit, url=url)

        response_headers = {key.lower(): value for key, value in response.headers.items()}
        final_url = response.geturl() or url
        return response.getcode(), response_headers, body, final_url


class Fetcher:
    def __init__(self, user_agent=DEFAULT_USER_AGENT, timeout=DEFAULT_TIMEOUT,
                 max_size=DEFAULT_MAX_SIZE, cache: HttpCache | None = None,
                 transport=None, verify_ssl=True, allow_meta_refresh=True,
                 cache_only=False):
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.timeout = timeout
        self.max_size = max_size
        self.cache = cache
        self.transport = transport or UrllibTransport(
            timeout=timeout, max_size=max_size, verify_ssl=verify_ssl)
        self.allow_meta_refresh = allow_meta_refresh
        self.cache_only = cache_only

    def fetch(self, url, headers=None, data=None, method='GET', force=False,
              allow_meta=True, _depth=0):
        url = clean_url(normalize_url(url))
        request_headers = {
            'User-Agent': self.user_agent,
            'Accept': ('application/rss+xml, application/atom+xml, '
                       'application/feed+json, application/xml;q=0.9, '
                       'text/html;q=0.8, */*;q=0.5'),
            'Accept-Encoding': 'gzip, deflate, br',
        }
        request_headers.update(headers or {})

        cached = self.cache.get(url) if self.cache else None
        if self.cache_only:
            if not cached:
                raise FetchError('URL is not in the cache', url=url)
            return Response(url=cached.get('url', url), status=200,
                            headers=cached.get('headers', {}),
                            body=cached.get('body', b''))
        if cached and not force:
            request_headers.update(self.cache.conditional_headers(url))

        status, response_headers, body, final_url = self.transport.request(
            url, request_headers, data=data, method=method)
        final_url = clean_url(final_url)

        if status == 304 and cached:
            self.cache.renew(url)
            return Response(url=cached.get('url', url), status=200,
                            headers=cached.get('headers', {}),
                            body=cached.get('body', b''))

        body = self._decompress(body, response_headers)
        response = Response(url=final_url, status=status,
                            headers=response_headers, body=body)

        if (allow_meta and self.allow_meta_refresh and _depth < 3
                and response.ok and response.is_html):
            target = meta_refresh_target(response.text, final_url)
            if target and target != final_url:
                return self.fetch(target, headers=headers, force=force,
                                  allow_meta=allow_meta, _depth=_depth + 1)

        if self.cache and status == 200:
            self.cache.store(url, status, response_headers, body, final_url=final_url)
        return response

    def resolve(self, url):
        """Follow redirects and return the final URL without keeping the body."""
        url = clean_url(normalize_url(url))
        headers = {'User-Agent': self.user_agent, 'Accept': '*/*'}
        for method in ('HEAD', 'GET'):
            try:
                status, _headers, _body, final_url = self.transport.request(
                    url, headers, method=method, max_size=65536)
            except FetchError:
                continue
            if status < 400:
                return clean_url(final_url)
        return url

    def _decompress(self, body, headers):
        header = headers.get('content-encoding', '')
        codings = [part.strip().lower() for part in header.split(',') if part.strip()]
        if not codings:
            return body

        # Content-Encoding lists codings in the order they were applied.
        for coding in reversed(codings):
            try:
                body = _decode_body(body, coding)
            except Exception:
                # Some servers advertise gzip/br without actually applying it.
                return body
        return body


def _decode_body(body, coding):
    if coding in ('gzip', 'x-gzip'):
        return _bounded(zlib.decompressobj(16 + zlib.MAX_WBITS), body)
    if coding == 'deflate':
        try:
            return _bounded(zlib.decompressobj(zlib.MAX_WBITS), body)
        except zlib.error:
            return _bounded(zlib.decompressobj(-zlib.MAX_WBITS), body)
    if coding == 'br':
        import brotli

        out = brotli.decompress(body)
        if len(out) > MAX_DECOMPRESSED_SIZE:
            raise ValueError('Decompressed response is too large')
        return out
    return body


def _bounded(decompressor, body):
    out = decompressor.decompress(body, MAX_DECOMPRESSED_SIZE)
    if decompressor.unconsumed_tail:
        raise ValueError('Decompressed response is too large')
    out += decompressor.flush()
    if len(out) > MAX_DECOMPRESSED_SIZE:
        raise ValueError('Decompressed response is too large')
    return out


def meta_refresh_target(html_text, base_url):
    """Return the URL advertised by a meta refresh/location tag, if any."""
    try:
        doc = lxml_html.document_fromstring(html_text)
    except (ValueError, TypeError):
        return None

    for meta in doc.xpath('//meta[@http-equiv]'):
        equiv = (meta.get('http-equiv') or '').strip().lower()
        content = meta.get('content') or ''
        if equiv not in ('refresh', 'location'):
            continue
        match = _META_REFRESH_RE.search(content)
        if not match:
            continue
        if equiv == 'refresh':
            delay = _META_DELAY_RE.match(content)
            if delay and int(delay.group(1)) > 5:
                continue
        target = urljoin(base_url, match.group(1).strip())
        if target.startswith(('http://', 'https://')):
            return target
    return None
