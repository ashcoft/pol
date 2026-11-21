"""Feed serialisation: RSS 2.0, JSON Feed, CSV, HTML and JSONP."""

from __future__ import annotations

import csv
import html
import io
import json
import re
from email.utils import format_datetime

from lxml import etree

from .parse import html_to_text, sanitize_html

CONTENT_TYPES = {
    'rss': 'application/rss+xml; charset=utf-8',
    'json': 'application/feed+json; charset=utf-8',
    'jsonp': 'application/javascript; charset=utf-8',
    'csv': 'text/csv; charset=utf-8',
    'html': 'text/html; charset=utf-8',
}

_CALLBACK_RE = re.compile(r'^[A-Za-z_$][A-Za-z0-9_$.]*$')
_NSMAP = {
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'atom': 'http://www.w3.org/2005/Atom',
    'dc': 'http://purl.org/dc/elements/1.1/',
}
_ATOM = '{%s}' % _NSMAP['atom']
_CONTENT = '{%s}' % _NSMAP['content']
_DC = '{%s}' % _NSMAP['dc']


def _iso(value):
    return value.isoformat().replace('+00:00', 'Z') if value else None


def _cdata(value):
    # lxml's CDATA helper does not split a terminator embedded in the value.
    return etree.CDATA(value.replace(']]>', ']]]]><![CDATA[>'))


def to_rss(feed, clip=False):
    rss = etree.Element('rss', version='2.0', nsmap=_NSMAP)
    channel = etree.SubElement(rss, 'channel')
    etree.SubElement(channel, 'title').text = feed.title or 'pol feed'
    etree.SubElement(channel, 'link').text = feed.link or feed.url
    etree.SubElement(channel, 'description').text = html_to_text(feed.description) or (feed.title or 'pol feed')
    if feed.language:
        etree.SubElement(channel, 'language').text = feed.language
    if feed.url:
        etree.SubElement(channel, _ATOM + 'link', rel='self', href=feed.url,
                         type='application/rss+xml')

    for item in feed.items:
        node = etree.SubElement(channel, 'item')
        etree.SubElement(node, 'title').text = item.title
        link = item.link or item.id
        if link:
            etree.SubElement(node, 'link').text = link
        if item.id or link:
            guid = etree.SubElement(node, 'guid')
            guid.text = item.id or link
            guid.set('isPermaLink', 'true' if link and guid.text == link else 'false')
        description = item.body(clip=True) if clip and item.content else item.summary
        if description:
            etree.SubElement(node, 'description').text = _cdata(description)
        if item.content:
            etree.SubElement(node, _CONTENT + 'encoded').text = _cdata(item.content)
        if item.date:
            etree.SubElement(node, 'pubDate').text = format_datetime(item.date)
        if item.author:
            etree.SubElement(node, _DC + 'creator').text = item.author
        for enclosure in item.enclosures:
            if not enclosure.get('url'):
                continue
            attrs = {'url': enclosure['url'],
                     'type': enclosure.get('type') or 'application/octet-stream'}
            if enclosure.get('length'):
                attrs['length'] = str(enclosure['length'])
            etree.SubElement(node, 'enclosure', **attrs)

    return etree.tostring(rss, encoding='utf-8', pretty_print=True,
                          xml_declaration=True).decode('utf-8')


def to_json(feed, indent=False, clip=False):
    data = {
        'version': 'https://jsonfeed.org/version/1.1',
        'title': feed.title or 'pol feed',
        'home_page_url': feed.link or None,
        'feed_url': feed.url or None,
        'description': html_to_text(feed.description) or None,
        'language': feed.language or None,
        'items': [],
    }
    for index, item in enumerate(feed.items):
        entry = {
            'id': item.id or item.link or str(index),
            'url': item.link or None,
            'title': item.title or None,
            'content_html': item.body(clip=clip) or None,
            'summary': html_to_text(item.summary) or None,
            'date_published': _iso(item.date),
            'authors': [{'name': item.author}] if item.author else None,
            'image': item.images[0] if item.images else None,
            'attachments': [
                {
                    'url': enclosure['url'],
                    'mime_type': enclosure.get('type') or 'application/octet-stream',
                    'size_in_bytes': int(enclosure['length'])
                    if str(enclosure.get('length') or '').isdigit() else None,
                }
                for enclosure in item.enclosures if enclosure.get('url')
            ] or None,
        }
        data['items'].append({key: value for key, value in entry.items()
                              if value not in (None, [], '')})
    return json.dumps(data, ensure_ascii=False, indent=2 if indent else None)


def to_csv(feed, clip=False):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['title', 'link', 'date', 'author', 'content'])
    for item in feed.items:
        writer.writerow([
            item.title,
            item.link,
            _iso(item.date) or '',
            item.author,
            html_to_text(item.body(clip=clip)),
        ])
    return buffer.getvalue()


def to_html(feed, clip=False):
    parts = [
        '<!DOCTYPE html>',
        '<html><head><meta charset="utf-8">',
        '<title>%s</title>' % html.escape(feed.title or 'pol feed'),
        '<style>body{font-family:sans-serif;max-width:46rem;margin:2rem auto;'
        'padding:0 1rem;line-height:1.5}article{margin-bottom:2rem}'
        'a{color:#0b5cad}.meta{color:#666;font-size:.9rem}</style>',
        '</head><body>',
        '<h1><a href="%s">%s</a></h1>' % (
            html.escape(feed.link or feed.url, quote=True),
            html.escape(feed.title or 'pol feed')),
    ]
    if feed.description:
        parts.append('<p class="meta">%s</p>' % html.escape(html_to_text(feed.description)))
    for item in feed.items:
        parts.append('<article>')
        if item.link:
            parts.append('<h2><a href="%s">%s</a></h2>' % (
                html.escape(item.link, quote=True), html.escape(item.title or item.link)))
        else:
            parts.append('<h2>%s</h2>' % html.escape(item.title))
        meta = [value for value in (
            _iso(item.date), item.author) if value]
        if meta:
            parts.append('<p class="meta">%s</p>' % html.escape(' · '.join(meta)))
        body = item.body(clip=clip)
        if '<' in body:
            parts.append(sanitize_html(body))
        elif body:
            parts.append('<p>%s</p>' % html.escape(body))
        parts.append('</article>')
    parts.append('</body></html>')
    return '\n'.join(parts)


def format_feed(feed, fmt='rss', indent=False, callback=None, clip=False):
    """Serialise a feed and return ``(body, content_type)``."""
    fmt = (fmt or 'rss').lower()
    if fmt == 'rss':
        return to_rss(feed, clip=clip), CONTENT_TYPES['rss']
    if fmt == 'json':
        return to_json(feed, indent=indent, clip=clip), CONTENT_TYPES['json']
    if fmt == 'csv':
        return to_csv(feed, clip=clip), CONTENT_TYPES['csv']
    if fmt == 'html':
        return to_html(feed, clip=clip), CONTENT_TYPES['html']
    if fmt == 'jsonp':
        if not callback or not _CALLBACK_RE.match(callback):
            raise ValueError('Invalid callback name')
        body = to_json(feed, indent=indent, clip=clip)
        return '%s(%s);' % (callback, body), CONTENT_TYPES['jsonp']
    raise ValueError('Unsupported format: %s' % fmt)
