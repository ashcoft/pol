"""Custom feeds built from JSON, HTML or XML documents with hand-written rules.

Rule keys follow morss (``items``, ``item_title``, ``item_link``, ...), so an
existing ``feedify.ini`` keeps working. JSON rules use dotted paths and the
``[]`` wildcard; HTML/XML rules use XPath.
"""

from __future__ import annotations

import configparser
import fnmatch
import json
import re
from dataclasses import dataclass, field
from html import escape as html_escape
from urllib.parse import urljoin

from lxml import etree
from lxml import html as lxml_html

from . import charset
from .errors import ParseError
from .model import Feed, Item
from .parse import absolutize, parse_date

_CLASS_RE = re.compile(r'\[class=([^\]]+)\]')


@dataclass
class Rules:
    mode: str = 'json'
    items: str = ''
    item_title: str = 'title'
    item_link: str = 'link'
    item_desc: str = 'description'
    item_content: str = 'content'
    item_time: str = 'date'
    item_author: str = 'author'
    item_image: str = 'image'
    item_id: str = 'id'
    title: str = ''
    desc: str = ''
    link: str = ''
    timeformat: str = ''
    path: tuple[str, ...] = field(default_factory=tuple)
    base: str = ''

    @classmethod
    def from_mapping(cls, mapping):
        if isinstance(mapping, Rules):
            return mapping
        values = dict(mapping or {})
        nested = values.pop('item', None) or {}
        for key in ('title', 'link', 'desc', 'content', 'time', 'author', 'image', 'id'):
            flat = 'item_' + key
            if flat in values and key not in nested:
                nested[key] = values.pop(flat)

        path = values.get('path') or ()
        if isinstance(path, str):
            path = tuple(part for part in path.splitlines() if part.strip())

        return cls(
            mode=(values.get('mode') or 'json').lower(),
            items=values.get('items') or '',
            item_title=nested.get('title', 'title'),
            item_link=nested.get('link', 'link'),
            item_desc=nested.get('desc', 'description'),
            item_content=nested.get('content', 'content'),
            item_time=nested.get('time', 'date'),
            item_author=nested.get('author', 'author'),
            item_image=nested.get('image', 'image'),
            item_id=nested.get('id', 'id'),
            title=values.get('title') or '',
            desc=values.get('desc') or values.get('description') or '',
            link=values.get('link') or '',
            timeformat=values.get('timeformat') or '',
            path=tuple(path),
            base=values.get('base') or '',
        )


def load_rules(path):
    """Load a JSON or INI rule file and return ``{name: Rules}``."""
    with open(path, encoding='utf-8') as handle:
        text = handle.read()

    stripped = text.lstrip()
    if stripped.startswith('{'):
        return _rules_from_json(json.loads(stripped))
    if stripped.startswith('[') and not path.lower().endswith(('.ini', '.cfg')):
        try:
            return _rules_from_json(json.loads(stripped))
        except ValueError:
            pass

    parser = configparser.RawConfigParser()
    parser.read_string(text)
    return {section: Rules.from_mapping(dict(parser.items(section)))
            for section in parser.sections()}


def _rules_from_json(data):
    if isinstance(data, list):
        return {str(index): Rules.from_mapping(entry) for index, entry in enumerate(data)}
    if isinstance(data, dict) and 'items' not in data and 'rules' not in data:
        named = {key: value for key, value in data.items()
                 if isinstance(value, dict) and ('items' in value or 'mode' in value)}
        if named and len(named) == len(data):
            return {key: Rules.from_mapping(value) for key, value in named.items()}
    if isinstance(data, dict) and isinstance(data.get('rules'), list):
        return {str(index): Rules.from_mapping(entry)
                for index, entry in enumerate(data['rules'])}
    return {'default': Rules.from_mapping(data)}


def rules_for_url(rules_by_name, url):
    for rules in rules_by_name.values():
        for pattern in rules.path:
            if fnmatch.fnmatch(url, pattern):
                return rules
    return None


def _path_parts(path):
    path = path.strip()
    if path in ('$', ''):
        return []
    if path.startswith('$.'):
        path = path[2:]

    parts = []
    for part in path.split('.'):
        if not part:
            continue
        if part.endswith(('[]', '[*]')):
            suffix = 3 if part.endswith('[*]') else 2
            parts.extend((part[:-suffix], '[]'))
        else:
            parts.append(part)
    return parts


def _get_path(value, path):
    if not path:
        return value
    current = value
    for part in _path_parts(path):
        if part in ('[]', '[*]'):
            return current
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.lstrip('-').isdigit():
            index = int(part)
            current = current[index] if -len(current) <= index < len(current) else None
        else:
            return None
        if current is None:
            return None
    return current


def _select_all(value, path):
    if not path:
        return value if isinstance(value, list) else [value]
    current = value
    for part in _path_parts(path):
        if part in ('[]', '[*]'):
            break
        current = _get_path(current, part)
        if current is None:
            return []
    if isinstance(current, list):
        return current
    return [] if current is None else [current]


def _as_text(value):
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _xpath(node, expression):
    expression = _CLASS_RE.sub(
        r'[@class and contains(concat(" ", normalize-space(@class), " "), " \1 ")]',
        expression)
    try:
        return node.xpath(expression)
    except etree.XPathError:
        return []


def _element_text(node):
    if hasattr(node, 'text_content'):
        return node.text_content()
    return ' '.join(node.itertext())


def _xpath_text(node, expression):
    if not expression:
        return ''
    matches = _xpath(node, expression)
    parts = []
    for match in matches:
        if isinstance(match, str):
            parts.append(match)
        else:
            parts.append(_element_text(match))
    return ' '.join(' '.join(part.split()) for part in parts if part).strip()


def _xpath_inner(node, expression):
    if not expression:
        return ''
    matches = _xpath(node, expression)
    parts = []
    for match in matches:
        if isinstance(match, str):
            parts.append(match)
        else:
            parts.append((html_escape(match.text) if match.text else '') + ''.join(
                etree.tostring(child, encoding='unicode', method='html')
                for child in match))
    return ''.join(parts).strip()


def _parse_json(text, url, rules):
    try:
        root = json.loads(text)
    except ValueError as exc:
        raise ParseError('Invalid JSON document') from exc

    feed = Feed(
        title=_as_text(_get_path(root, rules.title)) if rules.title else '',
        link=(_as_text(_get_path(root, rules.link)) if rules.link else '') or url,
        description=_as_text(_get_path(root, rules.desc)) if rules.desc else '',
        url=url,
        format='json',
    )
    for element in _select_all(root, rules.items):
        item = Item(
            title=_as_text(_get_path(element, rules.item_title)),
            link=_as_text(_get_path(element, rules.item_link)),
            id=_as_text(_get_path(element, rules.item_id)),
            summary=absolutize(_as_text(_get_path(element, rules.item_desc)), url),
            content=absolutize(_as_text(_get_path(element, rules.item_content)), url),
            date=parse_date(_get_path(element, rules.item_time)),
            author=_as_text(_get_path(element, rules.item_author)),
        )
        image = _as_text(_get_path(element, rules.item_image))
        if image:
            item.images.append(urljoin(url, image))
        if item.link:
            item.link = urljoin(url, item.link)
        feed.items.append(item)
    return feed


def _parse_markup(text, url, rules, mode):
    if mode == 'html':
        try:
            root = lxml_html.document_fromstring(text)
        except (ValueError, TypeError) as exc:
            raise ParseError('Invalid HTML document') from exc
    else:
        text = charset.strip_declaration(text)
        parser = etree.XMLParser(recover=True, resolve_entities=False,
                                 no_network=True, huge_tree=True)
        try:
            root = etree.fromstring(text.encode('utf-8'), parser=parser)
        except (etree.XMLSyntaxError, ValueError) as exc:
            raise ParseError('Invalid XML document') from exc
        if root is None:
            raise ParseError('Empty XML document')

    feed = Feed(
        title=_xpath_text(root, rules.title) if rules.title else '',
        link=(_xpath_text(root, rules.link) if rules.link else '') or url,
        description=_xpath_text(root, rules.desc) if rules.desc else '',
        url=url,
        format=mode,
    )
    nodes = _xpath(root, rules.items) if rules.items else [root]
    for node in nodes:
        if isinstance(node, str):
            continue
        item = Item(
            title=_xpath_text(node, rules.item_title),
            link=_xpath_text(node, rules.item_link),
            id=_xpath_text(node, rules.item_id),
            summary=absolutize(_xpath_inner(node, rules.item_desc), url),
            content=absolutize(_xpath_inner(node, rules.item_content), url),
            date=parse_date(_xpath_text(node, rules.item_time)),
            author=_xpath_text(node, rules.item_author),
        )
        image = _xpath_text(node, rules.item_image)
        if image:
            item.images.append(urljoin(url, image))
        if item.link:
            item.link = urljoin(url, item.link)
        feed.items.append(item)
    return feed


def parse_custom(data, url, rules):
    """Build a Feed from a JSON/HTML/XML document using hand-written rules."""
    rules = Rules.from_mapping(rules)
    if isinstance(data, bytes):
        text, _encoding = charset.decode(data)
    else:
        text = str(data)

    mode = rules.mode
    if mode in ('', 'auto'):
        mode = 'json' if text.lstrip().startswith(('{', '[')) else 'html'
    if mode == 'json':
        return _parse_json(text, url, rules)
    if mode in ('html', 'xml'):
        return _parse_markup(text, url, rules, mode)
    raise ParseError('Unsupported custom feed mode: %s' % mode)
