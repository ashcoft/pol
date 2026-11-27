"""HTTP fetching with compression, redirects, meta refresh and caching."""

from __future__ import annotations

import contextlib
import os
import re
import ssl
import zlib
from dataclasses import dataclass, field
from urllib import error, request as urllib_request
from urllib.parse import urljoin

from lxml import html as lxml_html

from . import charset
from .cache import HttpCache
from .errors import FetchError, InvalidURLError
from .safety import assert_public_url, resolve_addresses
from .urls import clean_url, normalize_url

DEFAULT_USER_AGENT = 'rssfinder/1.0'
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


def ensure_public_url(url, allow_private=False, resolve=True):
    """Reject destinations that resolve to non-public addresses.

    ``resolve=False`` skips the DNS lookup, which is what a cache hit needs: the literal
    host is still checked, but an offline read does not depend on a resolver.
    """
    if allow_private:
        return
    assert_public_url(url, resolve_addresses if resolve else None)


class GuardedRedirectHandler(urllib_request.HTTPRedirectHandler):
    """Rejects a redirect hop that points at a private or local destination."""

    def __init__(self, allow_private=False):
        self.allow_private = allow_private

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        ensure_public_url(urljoin(req.full_url, newurl), self.allow_private)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class UrllibTransport:
    """Default transport. Returns (status, headers, body, final_url)."""

    def __init__(self, timeout=DEFAULT_TIMEOUT, max_size=DEFAULT_MAX_SIZE,
                 verify_ssl=True, allow_private=None, block_private_hosts=False):
        self.timeout = timeout
        self.max_size = max_size
        if block_private_hosts:
            allow_private = False
        if allow_private is None:
            allow_private = False
        handlers = [GuardedRedirectHandler(allow_private)]
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
        except InvalidURLError:
            # The redirect guard rejected a hop; keep the guard's error type.
            raise
        except (error.URLError, OSError, ValueError) as exc:
            raise FetchError('Could not fetch %s: %s' % (url, exc), url=url) from exc

        try:
            body = response.read(limit + 1)
        except OSError as exc:
            raise FetchError('Could not read %s: %s' % (url, exc), url=url) from exc
        finally:
            with contextlib.suppress(Exception):
                response.close()

        if len(body) > limit:
            raise FetchError('Response is larger than %s bytes' % limit, url=url)

        response_headers = {key.lower(): value for key, value in response.headers.items()}
        final_url = response.geturl() or url
        return response.getcode(), response_headers, body, final_url


class Fetcher:
    def __init__(self, user_agent=DEFAULT_USER_AGENT, timeout=DEFAULT_TIMEOUT,
                 max_size=DEFAULT_MAX_SIZE, cache: HttpCache | None = None,
                 transport=None, verify_ssl=True, allow_meta_refresh=True,
                 cache_only=False, allow_private=None, block_private_hosts=None):
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.timeout = timeout
        self.max_size = max_size
        self.cache = cache
        if block_private_hosts is not None:
            allow_private = not block_private_hosts
        if allow_private is None:
            allow_private = os.environ.get('POL_READER_ALLOW_PRIVATE', '').strip().lower() in (
                '1', 'true', 'yes', 'on')
        self.allow_private = allow_private
        self.block_private_hosts = not allow_private
        self.transport = transport or UrllibTransport(
            timeout=timeout, max_size=max_size, verify_ssl=verify_ssl,
            allow_private=allow_private)
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

        # The cache is keyed by URL, so a POST body or another method must not
        # read or replace a cached GET response.
        is_get = method.upper() == 'GET' and data is None
        cached = self.cache.get(url) if (self.cache and is_get) else None
        if self.cache_only:
            if not cached:
                raise FetchError('URL is not in the cache', url=url)
            # A shared cache can hold a private feed; check the literal host, without DNS,
            # so an offline read still works.
            ensure_public_url(url, self.allow_private, resolve=False)
            response = Response(url=cached.get('url', url), status=200,
                                headers=cached.get('headers', {}),
                                body=cached.get('body', b''))
            followed = self._follow_meta(response, headers, force, allow_meta, _depth)
            return followed or response

        ensure_public_url(url, self.allow_private)
        if cached and not force:
            request_headers.update(self.cache.conditional_headers(url))

        status, response_headers, body, final_url = self.transport.request(
            url, request_headers, data=data, method=method)
        final_url = clean_url(final_url)
        # A redirect can land somewhere the requested URL would not have been allowed.
        ensure_public_url(final_url, self.allow_private)

        if status == 304 and cached:
            self.cache.renew(url)
            response = Response(url=cached.get('url', url), status=200,
                                headers=cached.get('headers', {}),
                                body=cached.get('body', b''))
            followed = self._follow_meta(response, headers, force, allow_meta, _depth)
            return followed or response

        body = self._decompress(body, response_headers)
        response = Response(url=final_url, status=status,
                            headers=response_headers, body=body)

        # Store the source response as well, so meta-refresh pages work offline.
        if self.cache and is_get and status == 200:
            self.cache.store(url, status, response_headers, body, final_url=final_url)

        followed = self._follow_meta(response, headers, force, allow_meta, _depth)
        return followed or response

    def _follow_meta(self, response, headers, force, allow_meta, depth):
        if not (allow_meta and self.allow_meta_refresh and depth < 3
                and response.ok and response.is_html):
            return None
        target = meta_refresh_target(response.text, response.url)
        if not target or target == response.url:
            return None
        return self.fetch(target, headers=headers, force=force,
                          allow_meta=allow_meta, _depth=depth + 1)

    def resolve(self, url):
        """Follow redirects and return the final URL without keeping the body."""
        url = clean_url(normalize_url(url))
        if self.cache_only:
            return url
        ensure_public_url(url, self.allow_private)
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
            except ValueError as exc:
                raise FetchError('Could not decompress response: %s' % exc) from exc
            except ImportError as exc:
                raise FetchError('Brotli support is not installed') from exc
            except Exception as exc:
                if isinstance(exc, zlib.error) or exc.__class__.__module__.startswith('brotli'):
                    # Some servers advertise gzip/br without actually applying it.
                    return body
                raise FetchError('Could not decompress response: %s' % exc) from exc
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

        decompressor = brotli.Decompressor()
        out = bytearray()
        for index in range(0, len(body), 4096):
            out.extend(decompressor.process(body[index:index + 4096]))
            if len(out) > MAX_DECOMPRESSED_SIZE:
                raise ValueError('Decompressed response is too large')
        if not decompressor.is_finished():
            raise ValueError('Incomplete brotli stream')
        return bytes(out)
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
