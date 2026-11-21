"""RSS, Atom, RDF and JSON Feed parsing with broken-input recovery."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape as html_escape
from html import unescape as html_unescape
from urllib.parse import urljoin

from lxml import etree
from lxml import html as lxml_html

from . import charset
from .errors import ParseError
from .model import Feed, Item

_IMAGE_URL_RE = re.compile(
    r'\.(?:jpe?g|png|gif|webp|avif|svg)(?:[?#]|$)', re.IGNORECASE)
# Types that say nothing about the payload, so an image-looking URL still counts.
_INCONCLUSIVE_TYPES = frozenset({'', 'application/octet-stream', 'binary/octet-stream'})
_DROP_TAGS = frozenset({'script', 'style', 'noscript', 'iframe', 'object',
                        'embed', 'form', 'input', 'button', 'svg', 'canvas'})
_LAZY_ATTRS = ('data-src', 'data-original', 'data-lazy-src', 'data-url')


def _local(element):
    tag = element.tag
    if not isinstance(tag, str):
        return ''
    return etree.QName(tag).localname.lower()


def _children(element, name):
    if element is None:
        return []
    return [child for child in element if _local(child) == name]


def _first(element, *names):
    for name in names:
        found = _children(element, name)
        if found:
            return found[0]
    return None


def _attr(element, name, default=''):
    return (element.get(name) or default).strip() if element is not None else default


def _value(element):
    """Text of a node, serialising child markup (Atom content, xhtml, ...)."""
    if element is None:
        return ''
    if len(element) == 0:
        return (element.text or '').strip()
    parts = [element.text or '']
    for child in element:
        parts.append(etree.tostring(child, encoding='unicode', method='html'))
    return ''.join(parts).strip()


def _text(element, *names):
    return _value(_first(element, *names))


def _atom_link(element, rel=None):
    fallback = ''
    for link in _children(element, 'link'):
        href = _attr(link, 'href')
        if not href:
            continue
        link_rel = (_attr(link, 'rel') or 'alternate').lower()
        if rel is None or link_rel == rel:
            return href
        fallback = fallback or href
    return fallback


def _enclosures(element):
    found = []

    def add(child):
        name = _local(child)
        url = _attr(child, 'url') or _attr(child, 'href') or _attr(child, 'src')
        if name not in ('enclosure', 'content', 'thumbnail', 'link') or not url:
            return
        if url.lower().startswith(('data:', 'javascript:')):
            return
        # MIME types may carry parameters, e.g. `application/octet-stream; name="a.jpg"`.
        kind = _attr(child, 'type').split(';')[0].strip()
        medium = _attr(child, 'medium').lower()
        if name == 'link' and (_attr(child, 'rel') or '').lower() != 'enclosure':
            return
        entry = {'url': url, 'type': kind or 'application/octet-stream',
                 'length': (_attr(child, 'length') or _attr(child, 'filesize')
                            or _attr(child, 'fileSize')),
                 'medium': medium}
        if name == 'thumbnail':
            # media:thumbnail already says the URL is artwork, even without a type.
            entry['thumbnail'] = True
        if entry not in found:
            found.append(entry)

    for child in element:
        name = _local(child)
        if name in ('enclosure', 'content', 'thumbnail', 'link'):
            add(child)
            # A media:thumbnail can sit inside the media:content it illustrates.
            for nested in _children(child, 'thumbnail'):
                add(nested)
        elif name == 'group':
            for nested in child:
                if _local(nested) in ('content', 'thumbnail'):
                    add(nested)
                    for deeper in _children(nested, 'thumbnail'):
                        add(deeper)

    return found


def parse_date(value):
    """Parse the many date formats found in feeds into an aware UTC datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    text = str(value).strip()
    if not text:
        return None

    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        parsed = None
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            parsed = None
    if parsed is None:
        try:
            from dateutil import parser as date_parser

            parsed = date_parser.parse(text)
        except (ImportError, ValueError, OverflowError, TypeError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def absolutize(fragment, base_url):
    """Resolve relative href/src values and promote lazy-loaded images."""
    if not fragment or '<' not in fragment or not base_url:
        return fragment
    try:
        root = lxml_html.fragment_fromstring(fragment, create_parent='div')
    except (etree.ParserError, ValueError, TypeError):
        return fragment

    for element in root.iter():
        tag = element.tag.lower() if isinstance(element.tag, str) else ''
        if tag in ('a', 'area') and element.get('href'):
            element.set('href', urljoin(base_url, element.get('href')))
        if tag in ('img', 'source', 'video', 'audio', 'iframe'):
            source = next((element.get(attr) for attr in _LAZY_ATTRS
                           if element.get(attr)), element.get('src'))
            if source and not source.lower().startswith(('data:', 'javascript:')):
                element.set('src', urljoin(base_url, source))
            for attr in _LAZY_ATTRS + ('loading',):
                element.attrib.pop(attr, None)
        if tag == 'img' and element.get('srcset'):
            element.set('srcset', _absolutize_srcset(element.get('srcset'), base_url))

    return _inner_html(root)


def _absolutize_srcset(value, base_url):
    candidates = []
    for candidate in value.split(','):
        parts = candidate.strip().split()
        if not parts:
            continue
        parts[0] = urljoin(base_url, parts[0])
        candidates.append(' '.join(parts))
    return ', '.join(candidates)


def sanitize_html(fragment):
    """Remove scripts, forms and inline event handlers from a feed fragment."""
    if not fragment or '<' not in fragment:
        return fragment
    try:
        root = lxml_html.fragment_fromstring(fragment, create_parent='div')
    except (etree.ParserError, ValueError, TypeError):
        return fragment

    for element in list(root.iter()):
        tag = element.tag.lower() if isinstance(element.tag, str) else ''
        if tag in _DROP_TAGS:
            drop_element(element)
            continue
        for attr in list(element.attrib):
            lowered = attr.lower()
            if lowered.startswith('on') or lowered in ('srcdoc', 'formaction'):
                del element.attrib[attr]
        for attr in ('href', 'src'):
            value = (element.get(attr) or '').strip().lower()
            if value.startswith('javascript:'):
                del element.attrib[attr]
    return _inner_html(root)


def drop_element(element):
    """Remove an element but keep the text that follows it."""
    parent = element.getparent()
    if parent is None:
        return
    tail = element.tail
    if tail:
        previous = element.getprevious()
        if previous is not None:
            previous.tail = (previous.tail or '') + tail
        else:
            parent.text = (parent.text or '') + tail
    parent.remove(element)


def _inner_html(element):
    # Text nodes are escaped here: a feed that writes `&lt;script&gt;` must come back as
    # text, not as markup the browser will execute.
    return (html_escape(element.text) if element.text else '') + ''.join(
        etree.tostring(child, encoding='unicode', method='html') for child in element)


_BASIC_ENTITY_RE = re.compile(r'&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]{1,31});')


def _unescape_basic(text):
    # Only entities that end with ';': a plain-text `&copy=` in a URL is not an entity and
    # must survive unchanged.
    return _BASIC_ENTITY_RE.sub(lambda match: html_unescape(match.group(0)), text)


def html_to_text(fragment):
    if not fragment:
        return ''
    if '<' not in fragment:
        return re.sub(r'\s+', ' ', _unescape_basic(fragment)).strip()
    try:
        root = lxml_html.fragment_fromstring(fragment, create_parent='div')
    except (etree.ParserError, ValueError, TypeError):
        return re.sub(r'<[^>]+>', ' ', fragment).strip()
    return re.sub(r'\s+', ' ', root.text_content()).strip()


def _is_image_enclosure(enclosure):
    if enclosure.get('thumbnail') or (enclosure.get('medium') or '') == 'image':
        return True
    kind = (enclosure.get('type') or '').lower()
    if kind.startswith('image/'):
        return True
    # An explicit audio/video type wins over an image-looking file extension.
    if kind not in _INCONCLUSIVE_TYPES:
        return False
    return bool(_IMAGE_URL_RE.search(enclosure.get('url') or ''))


def _first_img_src(fragment):
    """First usable <img src> in an HTML fragment, in document order."""
    if not fragment or '<' not in fragment:
        return ''
    try:
        root = lxml_html.fragment_fromstring(fragment, create_parent='div')
    except (etree.ParserError, ValueError, TypeError):
        return ''
    for element in root.iter('img'):
        if not isinstance(element.tag, str):
            continue
        # A lazy-loaded image keeps the real URL in data-src and a placeholder in src.
        candidates = [element.get('src')] + [element.get(attr) for attr in _LAZY_ATTRS]
        for candidate in candidates:
            source = (candidate or '').strip()
            if source and not source.lower().startswith(('data:', 'javascript:')):
                return source
    return ''


def _images(item, description, content):
    images = []
    for enclosure in item.enclosures:
        if _is_image_enclosure(enclosure) and enclosure['url'] not in images:
            images.append(enclosure['url'])
    for fragment in (content, description):
        source = _first_img_src(fragment)
        if source and source not in images:
            images.append(source)
    item.images = images


def _item_from_rss(element):
    link = _text(element, 'link')
    guid_element = _first(element, 'guid')
    guid = _value(guid_element)
    permalink = (_attr(guid_element, 'isPermaLink')
                 or _attr(guid_element, 'ispermalink'))
    if not link and guid and permalink.lower() != 'false':
        link = guid
    description = _text(element, 'description')
    content = _text(element, 'encoded', 'content')
    date = parse_date(_text(element, 'pubdate', 'published', 'updated', 'date', 'created'))
    item = Item(
        title=_text(element, 'title'),
        link=link,
        id=guid,
        summary=description,
        content=content,
        date=date,
        author=_text(element, 'creator', 'author'),
        enclosures=_enclosures(element),
    )
    _images(item, description, content)
    return item


def _item_from_atom(element):
    link = _atom_link(element, 'alternate') or _atom_link(element)
    content = _value(_first(element, 'content'))
    summary = _value(_first(element, 'summary'))
    author = _text(_first(element, 'author'), 'name') or _text(element, 'author')
    item = Item(
        title=_value(_first(element, 'title')),
        link=link,
        id=_text(element, 'id'),
        summary=summary,
        content=content,
        date=parse_date(_text(element, 'published', 'updated', 'issued', 'modified',
                              'created')),
        author=author,
        enclosures=_enclosures(element),
    )
    _images(item, summary, content)
    return item


def _parse_rss(root, url):
    channel = _first(root, 'channel')
    if channel is None:
        channel = root
    feed = Feed(
        title=_text(channel, 'title'),
        link=_text(channel, 'link'),
        description=_text(channel, 'description', 'subtitle'),
        language=_text(channel, 'language'),
        url=url,
        format='rss',
    )
    feed.items = [_item_from_rss(item) for item in _children(channel, 'item')]
    return feed


def _parse_rdf(root, url):
    channel = _first(root, 'channel')
    feed = Feed(
        title=_text(channel, 'title'),
        link=_text(channel, 'link'),
        description=_text(channel, 'description'),
        url=url,
        format='rdf',
    )
    feed.items = [_item_from_rss(item) for item in _children(root, 'item')]
    return feed


def _parse_atom(root, url):
    feed = Feed(
        title=_value(_first(root, 'title')),
        link=_atom_link(root, 'alternate') or _atom_link(root),
        description=_value(_first(root, 'subtitle')),
        language=_attr(root, 'lang'),
        url=url,
        format='atom',
    )
    feed.items = [_item_from_atom(entry) for entry in _children(root, 'entry')]
    return feed


def parse_json_feed(text, url=''):
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ParseError('Invalid JSON feed') from exc
    if not isinstance(data, dict) or 'items' not in data:
        raise ParseError('Not a JSON feed')
    entries = data.get('items')
    if not isinstance(entries, list):
        raise ParseError('JSON feed items must be a list')

    feed = Feed(
        title=str(data.get('title') or ''),
        link=str(data.get('home_page_url') or ''),
        description=str(data.get('description') or ''),
        language=str(data.get('language') or ''),
        url=str(data.get('feed_url') or url),
        format='json',
    )
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get('content_html'):
            content = str(entry['content_html'])
        else:
            content = html_escape(str(entry.get('content_text') or ''))
        summary = html_escape(str(entry.get('summary') or ''))

        authors = entry.get('authors')
        author = ''
        if isinstance(authors, list) and authors and isinstance(authors[0], dict):
            author = str(authors[0].get('name') or '')
        elif isinstance(entry.get('author'), dict):
            author = str(entry['author'].get('name') or '')

        enclosures = []
        attachments = entry.get('attachments')
        if isinstance(attachments, list):
            for attachment in attachments:
                if isinstance(attachment, dict) and attachment.get('url'):
                    enclosures.append({
                        'url': str(attachment['url']),
                        'type': str(attachment.get('mime_type') or 'application/octet-stream'),
                        'length': str(attachment.get('size_in_bytes') or ''),
                    })
        item = Item(
            title=str(entry.get('title') or ''),
            link=str(entry.get('url') or entry.get('external_url') or ''),
            id=str(entry.get('id') or ''),
            summary=summary,
            content=content,
            date=parse_date(entry.get('date_published') or entry.get('date_modified')),
            author=author,
            enclosures=enclosures,
        )
        _images(item, summary, content)
        if entry.get('image'):
            image = str(entry['image'])
            if image not in item.images:
                item.images.insert(0, image)
        feed.items.append(item)
    return feed


def _absolutize_feed(feed, base_url):
    if not base_url:
        return feed
    feed.link = urljoin(base_url, feed.link) if feed.link else feed.link
    for item in feed.items:
        if item.link:
            item.link = urljoin(base_url, item.link)
        item.summary = absolutize(item.summary, base_url)
        item.content = absolutize(item.content, base_url)
        item.images = [urljoin(base_url, image) for image in item.images]
        for enclosure in item.enclosures:
            enclosure['url'] = urljoin(base_url, enclosure['url'])
    return feed


def parse_feed(data, url='', content_type=''):
    """Parse a feed from bytes or text. Raises ParseError for non-feed input."""
    if isinstance(data, bytes):
        if content_type and 'json' in content_type.lower():
            text, _encoding = charset.decode(data, content_type)
        else:
            text = charset.decode_xml(data, content_type)
    else:
        text = charset.strip_declaration(str(data))

    stripped = text.lstrip('\ufeff \t\r\n')
    if stripped.startswith(('{', '[')):
        return _absolutize_feed(parse_json_feed(stripped, url), url)

    parser = etree.XMLParser(recover=True, resolve_entities=False,
                             no_network=True, huge_tree=True)
    try:
        root = etree.fromstring(stripped.encode('utf-8'), parser=parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise ParseError('Invalid XML feed') from exc
    if root is None:
        raise ParseError('Empty XML feed')

    tag = _local(root)
    if tag == 'feed':
        feed = _parse_atom(root, url)
    elif tag == 'rdf':
        feed = _parse_rdf(root, url)
    elif tag in ('rss', 'channel'):
        feed = _parse_rss(root, url)
    else:
        raise ParseError('Unknown feed format: %s' % (tag or 'empty'))
    return _absolutize_feed(feed, url)
