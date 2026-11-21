"""Full-text article extraction.

A compact readability-style scorer: text-heavy blocks inherit a score from
their paragraph children, class/id hints push article containers up and
navigation/sidebar containers down, and the best candidate is serialised with
absolute URLs.
"""

from __future__ import annotations

import re
from copy import deepcopy

from lxml import etree
from lxml import html as lxml_html

from .parse import absolutize

_BLOCK_TAGS = frozenset({'p', 'pre', 'td', 'blockquote', 'div', 'section', 'article'})
_DROP_TAGS = frozenset({
    'script', 'style', 'noscript', 'iframe', 'object', 'embed', 'form', 'input',
    'button', 'svg', 'canvas', 'nav', 'aside', 'footer',
})
_POSITIVE_RE = re.compile(
    r'article|content|entry|main|post|story|text|body|blog', re.IGNORECASE)
_NEGATIVE_RE = re.compile(
    r'comment|sidebar|footer|nav|menu|share|social|related|advert|banner|promo|'
    r'subscribe|popup|modal|cookie|breadcrumb|widget|meta', re.IGNORECASE)
_HIDDEN_RE = re.compile(r'display\s*:\s*none|visibility\s*:\s*hidden', re.IGNORECASE)


def _inner_html(element):
    return (element.text or '') + ''.join(
        etree.tostring(child, encoding='unicode', method='html') for child in element)


def _class_weight(element):
    signature = '%s %s' % (element.get('class') or '', element.get('id') or '')
    weight = 0
    if _NEGATIVE_RE.search(signature):
        weight -= 25
    if _POSITIVE_RE.search(signature):
        weight += 25
    return weight


def _is_hidden(element):
    if element.get('hidden') is not None:
        return True
    style = element.get('style') or ''
    return bool(_HIDDEN_RE.search(style))


def _strip_junk(document):
    for element in list(document.iter()):
        if not isinstance(element.tag, str):
            continue
        tag = element.tag.lower()
        if tag in _DROP_TAGS or _is_hidden(element) or _class_weight(element) <= -25:
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
            continue
        for attr in list(element.attrib):
            if attr.lower().startswith('on'):
                del element.attrib[attr]
        for attr in ('href', 'src'):
            if (element.get(attr) or '').strip().lower().startswith('javascript:'):
                del element.attrib[attr]


def _best_article(document):
    articles = [element for element in document.iter('article')
                if isinstance(element.tag, str)
                and len(element.text_content().strip()) >= 300]
    if articles:
        return max(articles, key=lambda element: len(element.text_content()))

    body = document.find('body')
    root = body if body is not None else document
    scores = {}

    for element in root.iter():
        if not isinstance(element.tag, str) or element.tag.lower() not in _BLOCK_TAGS:
            continue
        text = element.text_content().strip()
        if len(text) < 25:
            continue
        score = 1 + text.count(',') + text.count('，') + min(len(text) / 100, 3)
        parent = element.getparent()
        if parent is not None and parent is not root:
            scores[parent] = scores.get(parent, 0) + score
            grandparent = parent.getparent()
            if grandparent is not None and grandparent is not root:
                scores[grandparent] = scores.get(grandparent, 0) + score / 2

    for element in scores:
        scores[element] += _class_weight(element)

    if not scores:
        return root
    return max(scores, key=scores.get)


def _content_sibling(element):
    if not isinstance(element.tag, str):
        return False
    if element.tag.lower() not in _BLOCK_TAGS:
        return False
    if _class_weight(element) < 0 or _is_hidden(element):
        return False
    return len(element.text_content().strip()) >= 80


def _collect(best):
    container = lxml_html.Element('div')
    parent = best.getparent()
    if parent is None or (isinstance(best.tag, str) and best.tag.lower() == 'article'):
        container.append(deepcopy(best))
        return container

    for sibling in parent:
        if sibling is best or _content_sibling(sibling):
            container.append(deepcopy(sibling))
    if len(container) == 0:
        container.append(deepcopy(best))
    return container


def extract(html_text, url=''):
    """Return the main article as an HTML fragment, or '' when impossible."""
    if not html_text or not html_text.strip():
        return ''
    try:
        document = lxml_html.document_fromstring(html_text)
    except (ValueError, TypeError):
        return ''

    _strip_junk(document)
    article = _collect(_best_article(document))
    _strip_junk(article)

    fragment = _inner_html(article).strip()
    if len(re.sub(r'<[^>]+>', '', fragment).strip()) < 80:
        return ''
    return absolutize(fragment, url) if url else fragment
