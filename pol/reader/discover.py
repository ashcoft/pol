"""Feed discovery, ported from ashcoft/rss-finder (feedfinder-ts behaviour).

Discovery looks at ``<link rel="alternate">`` tags, feed-looking anchors, the
usual well-known feed paths, and finally verifies every candidate by parsing it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

from lxml import html as lxml_html

from .errors import FetchError, InvalidURLError, ParseError
from .http import Fetcher
from .parse import parse_feed
from .urls import clean_url, looks_like_feed_url, normalize_url

FEED_MIME_TYPES = frozenset({
    'application/rss+xml',
    'application/atom+xml',
    'application/rdf+xml',
    'application/feed+json',
})

# Relative paths tried under the page first, then under the origin. The list
# matches feedfinder-ts and keeps the blogspot paths pol already supported.
WELL_KNOWN_PATHS = (
    'feed', 'feed/', 'rss', 'rss.xml', 'atom.xml', 'feed.xml', 'index.xml',
    'atom.json', 'feed.json', 'rss.json', 'index.json', 'rss/',
    'feeds/posts/default', 'blog/feed', '?feed=rss2',
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


def _dedupe_refs(refs):
    unique = []
    seen = set()
    for ref in refs:
        url = clean_url(ref.url)
        if url in seen:
            continue
        seen.add(url)
        unique.append(ref)
    return unique


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


def _well_known_refs(base_url, under_page):
    """Well-known feed paths, either relative to the page or to its origin."""
    if under_page:
        base = base_url
    else:
        parts = urlsplit(base_url)
        base = urlunsplit((parts.scheme, parts.netloc, '/', '', ''))
    page = clean_url(base_url)
    refs = []
    seen = set()
    for path in WELL_KNOWN_PATHS:
        url = clean_url(urljoin(base, path))
        if url == page or url in seen:
            continue
        seen.add(url)
        refs.append(FeedRef(url=url, source='guess'))
    return refs


def page_candidates(base_url):
    """Well-known feed paths relative to the page URL."""
    return _well_known_refs(base_url, True)


def root_candidates(base_url):
    """Well-known feed paths on the page's origin, the fallback pass."""
    return _well_known_refs(base_url, False)


def common_candidates(base_url):
    """Every well-known candidate, page-relative first, then the origin."""
    refs = page_candidates(base_url)
    seen = {ref.url for ref in refs}
    refs.extend(ref for ref in root_candidates(base_url) if ref.url not in seen)
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
    seen_final = set()
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
        except (FetchError, InvalidURLError, ParseError):
            continue
        if not feed.items and not feed.title:
            continue
        final_url = clean_url(response.url or url)
        if final_url in seen_final:
            continue
        seen_final.add(final_url)
        verified.append(FeedRef(
            title=ref.title or feed.title,
            url=final_url,
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

    if not verify:
        return _dedupe_refs(refs + common_candidates(response.url))[:limit]

    # Well-known paths are tried under the page first, then under the origin,
    # the way feedfinder-ts falls back when a subpath has no feed of its own.
    verified = _verify(refs + page_candidates(response.url), fetcher, limit)
    if len(verified) < limit and not any(ref.source == 'guess' for ref in verified):
        verified = _dedupe_refs(
            verified + _verify(root_candidates(response.url), fetcher,
                               limit - len(verified)))
    return verified[:limit]
