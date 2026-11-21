"""Feed discovery, ported from ashcoft/rss-finder (feedfinder-ts behaviour).

Discovery looks at ``<link rel="alternate">`` tags, feed-looking anchors, the
usual well-known feed paths, and finally verifies every candidate by parsing it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

from lxml import html as lxml_html

from .errors import FetchError, ParseError
from .http import Fetcher
from .parse import parse_feed
from .urls import clean_url, looks_like_feed_url, normalize_url

FEED_MIME_TYPES = frozenset({
    'application/rss+xml',
    'application/atom+xml',
    'application/rdf+xml',
    'application/feed+json',
})

COMMON_PATHS = (
    '/feed', '/feed/', '/rss', '/rss.xml', '/atom.xml', '/feed.xml',
    '/index.xml', '/feeds/posts/default', '/blog/feed', '/?feed=rss2',
    '/feed.json',
)

_FEED_WORD_RE = re.compile(r'\b(?:rss|atom|feed)\b', re.IGNORECASE)


@dataclass
class FeedRef:
    title: str = ''
    url: str = ''
    type: str = ''
    source: str = ''

    def as_dict(self):
        return {'title': self.title, 'url': self.url, 'type': self.type}


def _origin(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, '', '', ''))


def discover_from_html(html_text, base_url):
    """Return feed references advertised by an HTML document."""
    try:
        document = lxml_html.document_fromstring(html_text)
    except (ValueError, TypeError):
        return []

    refs = []
    seen = set()

    def add(href, title='', mime='', source='link'):
        href = (href or '').strip()
        if not href or href.lower().startswith(('javascript:', 'mailto:', 'data:')):
            return
        absolute = clean_url(urljoin(base_url, href))
        if not absolute.startswith(('http://', 'https://')) or absolute in seen:
            return
        seen.add(absolute)
        refs.append(FeedRef(title=(title or '').strip(), url=absolute,
                            type=mime, source=source))

    for link in document.xpath('//link[@href]'):
        rel = (link.get('rel') or '').lower().split()
        if 'alternate' not in rel:
            continue
        mime = (link.get('type') or '').strip().lower()
        href = link.get('href') or ''
        if mime in FEED_MIME_TYPES or (not mime and looks_like_feed_url(href)):
            add(href, link.get('title') or '', mime)

    for anchor in document.xpath('//a[@href]'):
        href = anchor.get('href') or ''
        text = ' '.join(anchor.text_content().split())
        if looks_like_feed_url(href) or _FEED_WORD_RE.search(text):
            add(href, text, '', source='anchor')

    return refs


def common_candidates(base_url):
    """Well-known feed paths on the same origin as ``base_url``."""
    origin = _origin(base_url)
    page = clean_url(base_url)
    refs = []
    for path in COMMON_PATHS:
        url = origin + path
        if url != page:
            refs.append(FeedRef(url=url, source='guess'))
    return refs


def _feed_mime(response, feed):
    content_type = response.content_type
    if content_type in FEED_MIME_TYPES:
        return content_type
    return {
        'rss': 'application/rss+xml',
        'rdf': 'application/rdf+xml',
        'atom': 'application/atom+xml',
        'json': 'application/feed+json',
    }.get(feed.format, 'application/xml')


def _verify(refs, fetcher, limit):
    verified = []
    seen = set()
    attempts = 0
    for ref in refs:
        if len(verified) >= limit or attempts >= limit + 5:
            break
        url = clean_url(ref.url)
        if url in seen:
            continue
        seen.add(url)
        attempts += 1
        try:
            response = fetcher.fetch(url)
            if not response.ok:
                continue
            feed = parse_feed(response.body, response.url, response.content_type)
        except (FetchError, ParseError):
            continue
        if not feed.items and not feed.title:
            continue
        verified.append(FeedRef(
            title=ref.title or feed.title,
            url=response.url or url,
            type=ref.type or _feed_mime(response, feed),
            source=ref.source,
        ))
    return verified


def find_feeds(url, fetcher=None, verify=True, limit=10):
    """Find feeds for a page URL, or confirm that the URL is itself a feed."""
    fetcher = fetcher or Fetcher()
    url = normalize_url(url)
    response = fetcher.fetch(url)
    if not response.ok:
        raise FetchError('Remote server returned HTTP %s' % response.status,
                         url=url, status=response.status)

    if response.is_feed:
        try:
            feed = parse_feed(response.body, response.url, response.content_type)
        except ParseError:
            pass
        else:
            return [FeedRef(title=feed.title, url=response.url,
                            type=_feed_mime(response, feed), source='direct')]

    refs = []
    if response.is_html:
        refs.extend(discover_from_html(response.text, response.url))
    refs.extend(common_candidates(response.url))

    if not verify:
        unique = []
        seen = set()
        for ref in refs:
            url = clean_url(ref.url)
            if url in seen:
                continue
            seen.add(url)
            unique.append(ref)
        return unique[:limit]
    return _verify(refs, fetcher, limit)
