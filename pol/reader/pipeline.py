"""End-to-end feed processing used by the server, the CLI and the frontend."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

from lxml import etree
from lxml import html as lxml_html

from .cache import HttpCache, make_cache
from .discover import (
    FeedRef,
    discover_from_html,
    find_feeds,
    page_candidates,
    root_candidates,
)
from .errors import FetchError, InvalidURLError, ParseError
from .http import DEFAULT_MAX_SIZE, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT, Fetcher
from .jsonfeeds import Rules, parse_custom, rules_for_url
from .model import Feed
from .output import format_feed
from .parse import absolutize, html_to_text, parse_feed, strip_links
from .readability import extract
from .urls import clean_url, decode_feedsportal, is_http_url, normalize_url, unwrap_redirector


@dataclass
class Options:
    format: str = 'rss'
    fulltext: bool = True
    clip: bool = False
    proxy: bool = False
    resolve: bool = False
    cache: bool = False
    cache_only: bool = False
    force: bool = False
    indent: bool = False
    callback: str | None = None
    search: str | None = None
    post: str | None = None
    order: str = 'first'
    firstlink: bool = False
    nolink: bool = False
    noref: bool = False
    silent: bool = False
    xpath: str | None = None
    items: str | None = None
    item_link: str | None = None
    item_title: str | None = None
    item_content: str | None = None
    item_time: str | None = None
    item_desc: str | None = None
    item_author: str | None = None
    item_image: str | None = None
    mode: str | None = None
    rules: object = None
    max_items: int = 20
    timeout: float = DEFAULT_TIMEOUT
    max_size: int = DEFAULT_MAX_SIZE
    user_agent: str = DEFAULT_USER_AGENT
    cache_backend: str | None = None
    cache_dir: str | None = None
    cache_ttl: int = 3600
    redis_url: str | None = None
    verify_ssl: bool = True
    follow_meta: bool = True
    allow_private: bool | None = None


@dataclass
class ProcessResult:
    text: str
    feed: Feed
    content_type: str
    discovered: list[FeedRef] = field(default_factory=list)


def _build_fetcher(options):
    cache = None
    if options.cache or options.cache_only:
        backend = options.cache_backend
        if not backend:
            backend = 'diskcache' if options.cache_dir else 'memory'
        store = make_cache(backend, directory=options.cache_dir, url=options.redis_url)
        cache = HttpCache(store, ttl=options.cache_ttl)
    return Fetcher(
        user_agent=options.user_agent,
        timeout=options.timeout,
        max_size=options.max_size,
        cache=cache,
        verify_ssl=options.verify_ssl,
        allow_meta_refresh=options.follow_meta,
        cache_only=options.cache_only,
        allow_private=options.allow_private,
    )


def _rules_from_options(options, url):
    rules = options.rules
    if rules is not None:
        if isinstance(rules, Rules):
            return rules
        if isinstance(rules, dict):
            if 'items' in rules or 'mode' in rules or 'item' in rules:
                return Rules.from_mapping(rules)
            named = {name: Rules.from_mapping(value) for name, value in rules.items()}
            if named:
                return rules_for_url(named, url) or next(iter(named.values()))
            return Rules.from_mapping(rules)
        return Rules.from_mapping(rules)

    if not options.items:
        return None
    return Rules.from_mapping({
        'mode': options.mode or 'json',
        'items': options.items,
        'item_title': options.item_title or 'title',
        'item_link': options.item_link or 'link',
        'item_desc': options.item_desc or 'description',
        'item_content': options.item_content or 'content',
        'item_time': options.item_time or 'date',
        'item_author': options.item_author or 'author',
        'item_image': options.item_image or 'image',
    })


def _feed_from_page(response, fetcher, options):
    if not response.is_html:
        raise ParseError('Document is neither a feed nor an HTML page')
    refs = discover_from_html(response.text, response.url)
    refs.extend(page_candidates(response.url))
    refs.extend(root_candidates(response.url))
    seen = set()
    candidates = []
    for ref in refs:
        if ref.url in seen:
            continue
        seen.add(ref.url)
        candidates.append(ref)
    for ref in candidates[:20]:
        try:
            candidate = fetcher.fetch(ref.url, force=options.force)
            if not candidate.ok:
                continue
            return parse_feed(candidate.body, candidate.url, candidate.content_type)
        except (FetchError, InvalidURLError, ParseError):
            continue
    raise ParseError('No feed found at %s' % response.url)


def _extract_with_xpath(html_text, url, xpath):
    try:
        document = lxml_html.document_fromstring(html_text)
        nodes = document.xpath(xpath)
    except Exception:
        return ''
    if not nodes:
        return ''
    node = nodes[0]
    if isinstance(node, str):
        return node
    fragment = (node.text or '') + ''.join(
        etree.tostring(child, encoding='unicode', method='html') for child in node)
    return absolutize(fragment, url)


_WIKIPEDIA_ATOM = 'http*://*.wikipedia.org/w/api.php?*&feedformat=atom'


def _fragment_root(fragment):
    if not fragment or '<' not in fragment:
        return None
    try:
        return lxml_html.fragment_fromstring(fragment, create_parent='div')
    except (etree.ParserError, ValueError, TypeError):
        return None


def _first_href(fragment):
    root = _fragment_root(fragment)
    if root is None:
        return ''
    for anchor in root.iter('a'):
        href = (anchor.get('href') or '').strip()
        if href:
            return href
    return ''


def _wikipedia_link(fragment):
    root = _fragment_root(fragment)
    if root is None:
        return ''
    hrefs = root.xpath('//b/a/@href')
    return hrefs[0].strip() if hrefs else ''


def _reddit_link(fragment):
    root = _fragment_root(fragment)
    if root is None:
        return ''
    for anchor in root.iter('a'):
        if ' '.join(anchor.text_content().split()) == '[link]':
            return (anchor.get('href') or '').strip()
    return ''


def _fix_items(feed, options):
    """Port morss's ItemFix: normalise titles and recover the real item link."""
    feed_url = feed.url or feed.link or ''
    wikipedia = fnmatch.fnmatch(feed_url, _WIKIPEDIA_ATOM)
    reddit = (urlsplit(feed_url).hostname or '').lower() == 'www.reddit.com'
    for item in feed.items:
        if item.title and len(item.title) > 20 and item.title.isupper():
            item.title = item.title.title()
        if wikipedia:
            link = _wikipedia_link(item.summary)
            if link:
                item.link = link
        if options.firstlink:
            link = _first_href(item.summary) or _first_href(item.content)
            if link:
                item.link = link
        if item.link:
            item.link = decode_feedsportal(unwrap_redirector(item.link))
        if reddit and item.content:
            link = _reddit_link(item.content)
            if link:
                item.link = link
        if item.link:
            item.link = urljoin(feed_url, item.link)


def _items_to_process(feed, options):
    """Items to enrich, in processing order, without reordering the output."""
    limit = max(0, int(options.max_items))
    if limit == 0:
        return []
    items = list(feed.items)
    order = (options.order or 'first').lower()
    if order == 'last':
        return items[-limit:]
    if order in ('newest', 'oldest'):
        now = datetime.now(timezone.utc)
        ordered = sorted(items, key=lambda item: item.date or now)
        if order == 'newest':
            ordered.reverse()
        return ordered[:limit]
    return items[:limit]


def _apply_item_actions(feed, options):
    for item in feed.items:
        if options.nolink and item.content:
            item.content = strip_links(item.content)
        if options.noref:
            item.link = ''


def _fill_fulltext(feed, fetcher, options):
    for item in _items_to_process(feed, options):
        if not item.link or not is_http_url(item.link):
            continue
        if not options.clip and len(html_to_text(item.content or item.summary)) > 1000:
            continue
        try:
            response = fetcher.fetch(item.link, force=options.force, allow_meta=False)
        except (FetchError, InvalidURLError):
            continue
        if not response.ok or not response.is_html:
            continue
        article = ''
        if options.xpath:
            article = _extract_with_xpath(response.text, response.url, options.xpath)
        if not article:
            article = extract(response.text, response.url)
        if article:
            item.content = article


def _resolve_links(feed, fetcher, options):
    for item in _items_to_process(feed, options):
        if not item.link or not is_http_url(item.link):
            continue
        try:
            item.link = fetcher.resolve(clean_url(item.link))
        except InvalidURLError:
            continue


def _matches(item, needle):
    haystack = ' '.join((item.title, item.summary, item.content, item.link))
    return needle.lower() in haystack.lower()


def process(url, options=None, fetcher=None):
    """Read ``url`` as a feed (or discover one on the page) and format it."""
    options = options or Options()
    url = normalize_url(url)
    fetcher = fetcher or _build_fetcher(options)

    response = fetcher.fetch(
        url,
        force=options.force,
        allow_meta=options.follow_meta,
        data=options.post.encode('utf-8') if options.post is not None else None,
        method='POST' if options.post is not None else 'GET',
    )
    if response.status >= 400:
        raise FetchError('Remote server returned HTTP %s' % response.status,
                         url=url, status=response.status)

    rules = _rules_from_options(options, response.url)
    if rules is not None:
        feed = parse_custom(response.body, response.url, rules)
    else:
        try:
            feed = parse_feed(response.body, response.url, response.content_type)
        except ParseError:
            feed = _feed_from_page(response, fetcher, options)

    if not feed.url:
        feed.url = response.url or url
    if not feed.link:
        feed.link = response.url or url

    _fix_items(feed, options)
    if options.search:
        feed.items = [item for item in feed.items if _matches(item, options.search)]
    if options.resolve:
        _resolve_links(feed, fetcher, options)
    if options.fulltext and not options.proxy:
        _fill_fulltext(feed, fetcher, options)
    _apply_item_actions(feed, options)

    text, content_type = format_feed(
        feed, options.format, indent=options.indent,
        callback=options.callback, clip=options.clip)
    return ProcessResult(text=text, feed=feed, content_type=content_type)


def discover(url, options=None, fetcher=None):
    """Return feeds advertised by ``url`` (or the feed itself)."""
    options = options or Options()
    fetcher = fetcher or _build_fetcher(options)
    return find_feeds(url, fetcher=fetcher)
