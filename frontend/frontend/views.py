import urllib.error
import urllib.parse
import urllib.request
import json
import re

from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse

from . import settings as frontend_settings
from .forms import IndexForm
from .models import Feed, Field, FeedField
from .settings import DOWNLOADER_PAGE_URL, FEED_PAGE_URL
from .setup_tool import get_selection_tag_ids, build_xpathes_for_items
from .setup_tool_ext import build_xpath_results

DOWNLOADER_BASE_URL = getattr(frontend_settings, 'DOWNLOADER_BASE_URL', 'http://127.0.0.1:1234')

_SCHEME_RE = re.compile(r'^([a-z][a-z0-9+.-]*):(?!\d)', re.IGNORECASE)


def _normalize_discovery_url(url):
    """Mirror pol.reader.urls.normalize_url without importing the reader package."""
    trimmed = (url or '').strip()
    if not trimmed:
        raise ValueError('URL is required')
    scheme = _SCHEME_RE.match(trimmed)
    # The user-controlled value is deliberately the URL host; URLValidator below
    # rejects anything that is not a well-formed http(s) URL.
    candidate = trimmed if scheme else 'https://' + trimmed  # nosemgrep
    try:
        URLValidator(schemes=['http', 'https'])(candidate)
    except ValidationError as exc:
        raise ValueError('Invalid URL format') from exc
    return candidate

def index(request):
    if request.method == 'GET' and 'url' in request.GET:
        form = IndexForm(request.GET)
        if form.is_valid():
            val = URLValidator()
            try:
                url = request.GET['url']
                if not url.startswith('http'):
                    url = 'http://' + url
                val(url)
            except ValidationError:
                form.add_error('url', 'Invalid url')
            else:
                # The redirect target is always this site's setup page; the
                # user-supplied URL only becomes an encoded query parameter.
                return HttpResponseRedirect(
                    reverse('setup') + '?' + urllib.parse.urlencode({'url': url}))
    else:
        form = IndexForm()

    return render(request, 'frontend/index.html', {'form': form})

def contact(request):
    return render(request, 'frontend/contact.html')

@ensure_csrf_cookie
def setup(request):
    if request.method == 'GET' and 'url' in request.GET:
        external_page_url = DOWNLOADER_PAGE_URL + urllib.parse.quote(request.GET['url'], safe='')
        return render(request, 'frontend/setup.html',
                        {
                            'external_page_url': external_page_url,
                            'page_url': request.GET['url']
                        })

    return HttpResponseBadRequest('Url is required')

def _validate_html(html):

    def walk(tag):
        if (len(tag) != 3 or not isinstance(tag[0], str) or
                type(tag[1]) is not dict or 'tag-id' not in tag[1] or
                type(tag[2]) is not list):
            return False
        for t in tag[2]:
            if not walk(t):
                return False
        return True

    return walk(html)


def setup_get_selected_ids(request):
    if request.method == 'POST':
        obj = json.loads(request.body)
        if 'html' not in obj or 'names' not in obj:
            return HttpResponseBadRequest('"html" and "names" parameters are required')
        html_json = obj['html']
        item_names = obj['names']

        if not _validate_html(html_json):
            return HttpResponseBadRequest('html is invalid')

        xpathes = build_xpathes_for_items(item_names, html_json)
        if 'title' in xpathes[1]:
            xpathes[1]['link'] = _get_link_xpath(xpathes[1]['title'])
        if 'image' in xpathes[1]:
            xpathes[1]['image'] = _get_image_xpath(xpathes[1]['image'])
        if 'date' in xpathes[1]:
            xpathes[1]['date'] = _get_date_xpath(xpathes[1]['date'])

        resp = {
            'xpathes': xpathes,
            'ids': get_selection_tag_ids(item_names, html_json)
        }

        return HttpResponse(json.dumps(resp))


_CHILD_NODE_SUFFIX = '/child::node()'


def _xpath_base(xpath):
    if xpath == '.' + _CHILD_NODE_SUFFIX:
        return '.'
    if xpath.endswith(_CHILD_NODE_SUFFIX):
        return xpath[:-len(_CHILD_NODE_SUFFIX)]
    return xpath


def _get_link_xpath(title_xpath):
    base = _xpath_base(title_xpath)
    # The article link may be nested inside the title or wrap it.
    return ('(%s/descendant-or-self::node()/@href'
            ' | %s/ancestor-or-self::node()/@href)[1]') % (base, base)


def _get_image_xpath(image_xpath):
    # Keep the element path; pol.feed prefers data-src over src when reading it,
    # which avoids emitting lazy-loading placeholders.
    return _xpath_base(image_xpath)


def _get_date_xpath(date_xpath):
    base = _xpath_base(date_xpath)
    if base == '.':
        # A bare '.' cannot take a predicate in XPath 1.0.
        base = 'self::node()'
    # Prefer a non-empty machine-readable datetime; otherwise keep every child
    # node so a label split across elements is not truncated.
    return ('%s/@datetime[normalize-space(.)]'
            ' | %s[not(@datetime[normalize-space(.)])]/child::node()') % (base, base)


def _create_feed(url, xpathes, edited=False):
    feed_xpath = xpathes[0]
    item_xpathes = xpathes[1]

    fields = list(Field.objects.all())
    by_id = {field.id: field for field in fields}
    by_name = {by_id[field_id].name: value
               for field_id, value in item_xpathes.items() if field_id in by_id}

    with transaction.atomic():
        feed = Feed(uri=url, xpath=feed_xpath, edited=edited)
        feed.save()

        for field in fields:
            if field.name == 'link' and 'title' in by_name and not edited:
                xpath = _get_link_xpath(by_name['title'][0])
            elif field.name == 'image' and 'image' in by_name and not edited:
                xpath = _get_image_xpath(by_name['image'][0])
            elif field.name == 'date' and 'date' in by_name and not edited:
                xpath = _get_date_xpath(by_name['date'][0])
            elif field.id in item_xpathes:
                xpath = item_xpathes[field.id][0]
            else:
                continue
            FeedField(feed=feed, field=field, xpath=xpath).save()

    return feed.id

def setup_create_feed(request):
    if request.method == 'POST':
        obj = json.loads(request.body)
        if 'html' not in obj or 'names' not in obj or 'url' not in obj:
            return HttpResponseBadRequest('"html", "names" and "url" parameters are required')
        html_json = obj['html']
        item_names = obj['names']
        url = obj['url']

        if not _validate_html(html_json):
            return HttpResponseBadRequest('html is invalid')

        xpathes = build_xpathes_for_items(item_names, html_json)

        field_xpathes = {}
        for field in Field.objects.all():
            if field.name not in xpathes[1]:
                continue
            required = field.name in ('title', 'description')
            field_xpathes[field.id] = [xpathes[1][field.name], required]
        xpathes[1] = field_xpathes

        feed_id = _create_feed(url, xpathes)

        return HttpResponse(reverse('preview', args=(feed_id,)))

def _validate_selectors(selectors):
    if not isinstance(selectors, list) or len(selectors) != 2:
        return False
    feed_xpath = selectors[0]
    item_xpathes = selectors[1]

    if not isinstance(feed_xpath, str):
        return False
    if not isinstance(item_xpathes, dict):
        return False

    fields = list(Field.objects.all())
    by_name = {field.name: field for field in fields}
    by_id = {field.id: field for field in fields}

    item_xpathes_out = {}

    for key, xpath in item_xpathes.items():
        field = by_name.get(key)
        if field is None:
            try:
                field = by_id.get(int(key))
            except (TypeError, ValueError):
                field = None
        if field is None:
            continue
        if not isinstance(xpath, str):
            return False
        item_xpathes_out[field.id] = [xpath, field.required]
    return [feed_xpath, item_xpathes_out]


def _name_field_results(messages, posts):
    names = {field.id: field.name for field in Field.objects.all()}
    feed_result, field_results = messages
    field_results = {names.get(field_id, field_id): value
                     for field_id, value in field_results.items()}
    posts = [{names.get(field_id, field_id): value for field_id, value in post.items()}
             for post in posts]
    return [feed_result, field_results], posts


def setup_validate_selectors(request):
    if request.method == 'POST':
        obj = json.loads(request.body)
        if 'selectors' not in obj or 'snapshot_time' not in obj:
            return HttpResponseBadRequest('"selectors" and "snapshot_time" are required')

        selectors = obj['selectors']
        file_name = obj['snapshot_time']

        if not re.match(r'^\d{10}\.\d+_[\da-f]{32,64}\Z', file_name):
            return HttpResponseBadRequest('"snapshot_time" is invalid')

        validated_selectors = _validate_selectors(selectors)

        if not validated_selectors:
            return HttpResponseBadRequest('selectors are invalid')

        messages, posts, success = build_xpath_results(validated_selectors, file_name)
        messages, posts = _name_field_results(messages, posts)

        return HttpResponse(json.dumps({'success': success, 'messages': messages, 'posts': posts}))

def setup_create_feed_ext(request):
    if request.method == 'POST':
        obj = json.loads(request.body)
        if 'selectors' not in obj or 'snapshot_time' not in obj or 'url' not in obj:
            return HttpResponseBadRequest('"selectors", "snapshot_time" and "url" are required')

        selectors = obj['selectors']
        file_name = obj['snapshot_time']

        if not re.match(r'^\d{10}\.\d+_[\da-f]{32,64}\Z', file_name):
            return HttpResponseBadRequest('"snapshot_time" is invalid')

        validated_selectors = _validate_selectors(selectors)

        if not validated_selectors:
            return HttpResponseBadRequest('selectors are invalid')

        messages, posts, success = build_xpath_results(validated_selectors, file_name)
        messages, posts = _name_field_results(messages, posts)

        if success:
            url = obj['url']
            feed_id = _create_feed(url, validated_selectors, True)
            return HttpResponse(json.dumps({'success': True, 'url': reverse('preview', args=(feed_id,))}))
        else:
            return HttpResponse(json.dumps({'success': False, 'messages': messages}))

def preview(request, feed_id):
    if request.method == 'GET': 
        return render(request, 'frontend/preview.html',
                        {
                            'feed_url': FEED_PAGE_URL + feed_id
                        })

    return HttpResponseBadRequest('Only GET method supported')


def discover(request):
    """Proxy feed discovery to the downloader (used by the index page and dev)."""
    url = (request.GET.get('url') or '').strip()
    if not url:
        return HttpResponseBadRequest('Url is required')
    try:
        url = _normalize_discovery_url(url)
    except ValueError:
        return HttpResponseBadRequest('Invalid url')

    if not url.startswith(('http://', 'https://')):
        return HttpResponseBadRequest('Invalid url')

    target = DOWNLOADER_BASE_URL.rstrip('/') + '/discover?' + urllib.parse.urlencode({'url': url})
    try:
        with urllib.request.urlopen(target, timeout=10) as response:  # nosec B310
            payload = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        return HttpResponse(exc.read(), status=exc.code,
                            content_type='application/json')
    except Exception:
        return HttpResponse(json.dumps({'error': 'Feed discovery failed'}),
                            status=502, content_type='application/json')
    return HttpResponse(payload, status=status, content_type='application/json')
