import urllib.error
import urllib.parse
import urllib.request
import json
import re

from lxml import etree

from django.contrib.auth import login as auth_login, logout as auth_logout
from django.conf import settings as django_settings
from django.db.models import Count
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import (
    HttpResponseRedirect, HttpResponse, HttpResponseBadRequest,
    HttpResponseNotAllowed)
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from . import settings as frontend_settings
from .forms import FeedEditForm, IndexForm, LoginForm, SignUpForm
from .models import Feed, Field, FeedField
from .settings import DOWNLOADER_PAGE_URL, FEED_PAGE_URL
from .setup_tool import get_selection_tag_ids, build_xpathes_for_items
from .urlutils import normalize_discovery_url as _normalize_discovery_url

DOWNLOADER_BASE_URL = getattr(frontend_settings, 'DOWNLOADER_BASE_URL', 'http://127.0.0.1:1234')


def _session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _feed_owner_kwargs(request):
    if request.user.is_authenticated:
        return {'owner': request.user, 'session_key': ''}
    return {'owner': None, 'session_key': _session_key(request)}


def _can_manage(request, feed, allow_legacy_claim=False):
    if feed.owner_id is not None:
        return request.user.is_authenticated and feed.owner_id == request.user.id
    if feed.session_key:
        return feed.session_key == request.session.session_key
    # Feeds created before accounts existed have neither an owner nor a session.
    # They may be claimed by a signed-in user through the edit page, but never
    # deleted directly.
    return allow_legacy_claim and request.user.is_authenticated


def _deny_feed_access(request):
    if not request.user.is_authenticated:
        login_url = reverse('login') + '?' + urllib.parse.urlencode(
            {'next': request.get_full_path()})
        return HttpResponseRedirect(login_url)
    raise PermissionDenied(_('You cannot manage this feed.'))


def _claim_session_feeds(request, user):
    session_key = request.session.session_key
    if not session_key:
        return
    Feed.objects.filter(owner__isnull=True, session_key=session_key).update(
        owner=user, session_key='')


def index(request):
    if request.method == 'GET' and 'url' in request.GET:
        form = IndexForm(request.GET)
        if form.is_valid():
            try:
                url = _normalize_discovery_url(request.GET['url'])
            except ValueError:
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
    return render(request, 'frontend/contact.html',
                  {'contact_url': getattr(django_settings, 'CONTACT_URL', '')})

class _BadRequest(Exception):
    def __init__(self, message, captcha=False):
        super().__init__(message)
        self.message = message
        self.captcha = captcha


class _SetupDenied(Exception):
    pass


def _normalize_setup_url(raw_url):
    """Return a validated, public http(s) URL or raise _BadRequest."""
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise _BadRequest('Url is required')
    try:
        url = _normalize_discovery_url(raw_url)
    except ValueError as exc:
        raise _BadRequest('Invalid url') from exc

    if not getattr(django_settings, 'READER_ALLOW_PRIVATE', False):
        from pol.reader.errors import InvalidURLError, UnresolvableURLError
        from pol.reader.safety import assert_public_url
        try:
            assert_public_url(url)
        except UnresolvableURLError as exc:
            raise _BadRequest('This URL could not be resolved.') from exc
        except InvalidURLError as exc:
            raise _BadRequest('This URL is not allowed.') from exc
    return url


def _setup_target(request):
    feed_id = request.GET.get('feed_id')
    feed = None
    if feed_id:
        if not str(feed_id).isdigit():
            raise _BadRequest('Invalid feed id')
        feed = get_object_or_404(Feed, pk=feed_id)
        if not _can_manage(request, feed, allow_legacy_claim=True):
            raise _SetupDenied()
        raw_url = feed.uri
    else:
        raw_url = request.GET.get('url', '')

    url = _normalize_setup_url(raw_url)
    return feed, url


@ensure_csrf_cookie
def setup(request):
    if request.method != 'GET':
        return HttpResponseBadRequest('Only GET method supported')
    try:
        feed, url = _setup_target(request)
    except _SetupDenied:
        return _deny_feed_access(request)
    except _BadRequest as exc:
        return HttpResponseBadRequest(exc.message, content_type='text/plain')

    setup_initial = None
    if feed:
        item_xpathes = {
            feed_field.field.name: feed_field.xpath
            for feed_field in feed.feedfield_set.select_related('field')
        }
        setup_initial = {
            'feed_id': feed.id,
            'selectors': [feed.xpath, item_xpathes],
        }

    external_page_url = DOWNLOADER_PAGE_URL + urllib.parse.quote(url, safe='')
    return render(request, 'frontend/setup.html',
                  {
                      'external_page_url': external_page_url,
                      'page_url': url,
                      'feed_id': feed.id if feed else None,
                      'setup_initial': setup_initial,
                  })


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


def _save_feed_fields(feed, xpathes, edited):
    feed_xpath = xpathes[0]
    item_xpathes = xpathes[1]

    fields = list(Field.objects.all())
    by_id = {field.id: field for field in fields}
    by_name = {by_id[field_id].name: value
               for field_id, value in item_xpathes.items() if field_id in by_id}

    feed.xpath = feed_xpath
    feed.edited = edited
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
            xpath = ''

        existing = FeedField.objects.filter(feed=feed, field=field).first()
        if xpath:
            if existing:
                existing.xpath = xpath
                existing.save(update_fields=['xpath'])
            else:
                FeedField.objects.create(feed=feed, field=field, xpath=xpath)
        elif existing:
            existing.delete()


def _duplicate_key(url):
    """Normalize a feed URL for duplicate detection.

    Fragments never reach the origin and a bare host is the same page as its
    root path, so both are folded into one key.
    """
    normalized = _normalize_discovery_url(url)
    parts = urllib.parse.urlsplit(normalized)
    return urllib.parse.urlunsplit((
        parts.scheme, parts.netloc, parts.path or '/', parts.query, ''))


def _same_feed_url(left, right):
    try:
        return _duplicate_key(left) == _duplicate_key(right)
    except ValueError:
        return left == right


def _find_duplicate_feed(request, url, exclude_id=None):
    try:
        normalized = _duplicate_key(url)
    except ValueError:
        return None
    feeds = _feeds_for_request(request)
    if exclude_id is not None:
        feeds = feeds.exclude(pk=exclude_id)
    for feed in feeds.only('id', 'uri'):
        try:
            if _duplicate_key(feed.uri) == normalized:
                return feed
        except ValueError:
            continue
    return None


def _create_feed(request, url, xpathes, edited=False):
    duplicate = _find_duplicate_feed(request, url)
    if duplicate is not None:
        return duplicate.id, True

    with transaction.atomic():
        feed = Feed(uri=url, xpath=xpathes[0], edited=edited,
                    **_feed_owner_kwargs(request))
        feed.save()
        _save_feed_fields(feed, xpathes, edited)

    return feed.id, False


def _update_feed(request, feed, url, xpathes, edited=True):
    if not _same_feed_url(feed.uri, url):
        duplicate = _find_duplicate_feed(request, url, exclude_id=feed.id)
        if duplicate is not None:
            return duplicate.id, True

    with transaction.atomic():
        feed = get_object_or_404(
            Feed.objects.select_for_update(), pk=feed.pk)
        if not _can_manage(request, feed, allow_legacy_claim=True):
            return None, False

        if request.user.is_authenticated and feed.owner_id is None:
            feed.owner = request.user
            feed.session_key = ''
        feed.uri = url
        feed.save()
        _save_feed_fields(feed, xpathes, edited)

    return feed.id, False


def _feed_for_update(payload):
    feed_id = payload.get('feed_id')
    if not feed_id:
        return None
    if not str(feed_id).isdigit():
        raise ValueError('Invalid feed id')
    return get_object_or_404(Feed, pk=feed_id)


def setup_create_feed(request):
    if request.method == 'POST':
        try:
            obj = json.loads(request.body)
        except (TypeError, ValueError):
            return HttpResponseBadRequest('Invalid JSON body')
        if 'html' not in obj or 'names' not in obj or 'url' not in obj:
            return HttpResponseBadRequest('"html", "names" and "url" parameters are required')
        html_json = obj['html']
        item_names = obj['names']
        try:
            url = _normalize_setup_url(obj['url'])
        except _BadRequest as exc:
            return HttpResponseBadRequest(exc.message, content_type='text/plain')

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

        if not xpathes[0].strip() or not field_xpathes:
            return HttpResponseBadRequest('Select at least one field.')

        try:
            feed = _feed_for_update(obj)
        except ValueError:
            return HttpResponseBadRequest('Invalid feed id')

        duplicate = False
        if feed:
            feed_id, duplicate = _update_feed(
                request, feed, url, xpathes, edited=False)
            if feed_id is None:
                return _deny_feed_access(request)
        else:
            feed_id, duplicate = _create_feed(request, url, xpathes)

        preview_url = reverse('preview', args=(feed_id,))
        if duplicate:
            preview_url += '?duplicate=1'
        return HttpResponse(preview_url, content_type='text/plain')

def _validate_selectors(selectors):
    if not isinstance(selectors, list) or len(selectors) != 2:
        return False
    feed_xpath, item_xpathes = selectors
    if not isinstance(feed_xpath, str) or not isinstance(item_xpathes, dict):
        return False
    if not feed_xpath.strip() or not item_xpathes:
        return False

    fields = list(Field.objects.all())
    by_name = {field.name: field for field in fields}
    by_id = {field.id: field for field in fields}

    result = {}
    for key, xpath in item_xpathes.items():
        field = by_name.get(key)
        if field is None and str(key).isdigit():
            field = by_id.get(int(key))
        if field is None or not isinstance(xpath, str):
            return False
        result[field.id] = [xpath, field.required]

    return [feed_xpath, result]


def _name_field_results(messages, posts):
    names = {field.id: field.name for field in Field.objects.all()}
    feed_result, field_results = messages
    field_results = {names.get(field_id, field_id): value
                     for field_id, value in field_results.items()}
    posts = [{names.get(field_id, field_id): value for field_id, value in post.items()}
             for post in posts]
    return [feed_result, field_results], posts


def setup_validate_selectors(request):
    from .setup_tool_ext import build_xpath_results

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

def _setup_ext_payload(request):
    try:
        obj = json.loads(request.body)
    except (TypeError, ValueError) as exc:
        raise _BadRequest('Invalid JSON body') from exc
    if 'selectors' not in obj or 'snapshot_time' not in obj or 'url' not in obj:
        raise _BadRequest(
            '"selectors", "snapshot_time" and "url" are required')
    file_name = obj['snapshot_time']
    if not re.match(r'^\d{10}\.\d+_[\da-f]{32,64}\Z', file_name):
        raise _BadRequest('"snapshot_time" is invalid')
    selectors = _validate_selectors(obj['selectors'])
    if not selectors:
        raise _BadRequest('selectors are invalid')
    return obj, selectors, file_name


def setup_create_feed_ext(request):
    from .setup_tool_ext import build_xpath_results

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        obj, selectors, file_name = _setup_ext_payload(request)
        url = _normalize_setup_url(obj['url'])
        messages, posts, success = build_xpath_results(selectors, file_name)
        messages, posts = _name_field_results(messages, posts)
        if not success:
            return HttpResponse(
                json.dumps({'success': False, 'messages': messages}),
                content_type='application/json')

        feed = _feed_for_update(obj)
        duplicate = False
        if feed:
            feed_id, duplicate = _update_feed(
                request, feed, url, selectors, True)
            if feed_id is None:
                raise _SetupDenied()
        else:
            feed_id, duplicate = _create_feed(
                request, url, selectors, True)
        preview_url = reverse('preview', args=(feed_id,))
        if duplicate:
            preview_url += '?duplicate=1'
        return HttpResponse(
            json.dumps({'success': True, 'url': preview_url}),
            content_type='application/json')
    except _BadRequest as exc:
        return HttpResponseBadRequest(exc.message, content_type='text/plain')
    except ValueError:
        return HttpResponseBadRequest('Invalid feed id')
    except _SetupDenied:
        return _deny_feed_access(request)


def preview(request, feed_id):
    if request.method != 'GET':
        return HttpResponseBadRequest('Only GET method supported')

    # The preview page itself does not need the database. The edit route
    # enforces ownership, so it is safe to show the link to everyone.
    return render(request, 'frontend/preview.html',
                  {
                      'feed_url': FEED_PAGE_URL + feed_id,
                      'feed_id': feed_id,
                      'duplicate': request.GET.get('duplicate'),
                  })


def _feeds_for_request(request):
    if request.user.is_authenticated:
        return Feed.objects.filter(owner=request.user)
    if request.session.session_key:
        return Feed.objects.filter(
            owner__isnull=True, session_key=request.session.session_key)
    return Feed.objects.none()


def myfeeds(request):
    feeds = list(_feeds_for_request(request).annotate(
        field_count=Count('feedfield')).order_by('-created'))
    keys = {}
    for feed in feeds:
        try:
            key = _duplicate_key(feed.uri)
        except ValueError:
            key = feed.uri
        feed.duplicate_key = key
        keys[key] = keys.get(key, 0) + 1
    for feed in feeds:
        feed.duplicate = keys[feed.duplicate_key] > 1
    return render(request, 'frontend/myfeeds.html',
                  {'feeds': feeds, 'feed_page_url': FEED_PAGE_URL})


def myfeeds_opml(request):
    feeds = _feeds_for_request(request).order_by('id')

    opml = etree.Element('opml', version='2.0')
    head = etree.SubElement(opml, 'head')
    etree.SubElement(head, 'title').text = 'RSS Finder feeds'
    body = etree.SubElement(opml, 'body')
    group = etree.SubElement(body, 'outline', text='RSS Finder', title='RSS Finder')
    for feed in feeds:
        etree.SubElement(
            group, 'outline', type='rss', text=feed.uri, title=feed.uri,
            xmlUrl=request.build_absolute_uri(FEED_PAGE_URL + str(feed.id)),
            htmlUrl=feed.uri)

    payload = etree.tostring(opml, encoding='utf-8', xml_declaration=True)
    return HttpResponse(payload, content_type='text/x-opml; charset=utf-8')


def edit_feed(request, feed_id):
    feed = get_object_or_404(Feed, pk=feed_id)
    fields = list(Field.objects.order_by('id'))

    if request.method == 'POST':
        form = FeedEditForm(request.POST, fields=fields)
        if form.is_valid():
            if not _can_manage(request, feed, allow_legacy_claim=True):
                return _deny_feed_access(request)

            duplicate = None
            if not _same_feed_url(feed.uri, form.cleaned_data['uri']):
                duplicate = _find_duplicate_feed(
                    request, form.cleaned_data['uri'], exclude_id=feed.id)
            if duplicate is not None:
                form.add_error(
                    'uri', _('You already have a feed for this page.'))
            else:
                with transaction.atomic():
                    # Reload under a row lock so two concurrent claims cannot
                    # both pass the permission check and overwrite each other.
                    feed = get_object_or_404(
                        Feed.objects.select_for_update(), pk=feed_id)
                    if not _can_manage(request, feed, allow_legacy_claim=True):
                        return _deny_feed_access(request)

                    if request.user.is_authenticated and feed.owner_id is None:
                        feed.owner = request.user
                        feed.session_key = ''
                    feed.uri = form.cleaned_data['uri']
                    feed.xpath = form.cleaned_data['feed_xpath']
                    feed.edited = True
                    feed.save()

                    for field in fields:
                        xpath = form.cleaned_data.get(
                            'xpath_%s' % field.name, '').strip()
                        existing = FeedField.objects.filter(
                            feed=feed, field=field).first()
                        if xpath:
                            if existing:
                                existing.xpath = xpath
                                existing.save(update_fields=['xpath'])
                            else:
                                FeedField.objects.create(
                                    feed=feed, field=field, xpath=xpath)
                        elif existing:
                            existing.delete()
                return redirect('preview', feed.id)
        if not _can_manage(request, feed, allow_legacy_claim=True):
            return _deny_feed_access(request)
    else:
        if not _can_manage(request, feed, allow_legacy_claim=True):
            return _deny_feed_access(request)
        initial = {'uri': feed.uri, 'feed_xpath': feed.xpath}
        for feed_field in feed.feedfield_set.select_related('field'):
            initial['xpath_%s' % feed_field.field.name] = feed_field.xpath
        form = FeedEditForm(initial=initial, fields=fields)

    return render(request, 'frontend/edit_feed.html',
                  {'feed': feed, 'form': form, 'field_rows': form.field_rows()})


def delete_feed(request, feed_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    feed = get_object_or_404(Feed, pk=feed_id)
    # Deleting an unclaimed legacy feed is not allowed. A user must claim it
    # through the edit page first.
    if not _can_manage(request, feed):
        raise PermissionDenied(_('You cannot delete this feed.'))
    feed.delete()
    return redirect('myfeeds')


def signup(request):
    if request.user.is_authenticated:
        return redirect('myfeeds')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            _claim_session_feeds(request, user)
            auth_login(request, user)
            return redirect('myfeeds')
    else:
        form = SignUpForm()

    return render(request, 'registration/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('myfeeds')

    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            _claim_session_feeds(request, user)
            auth_login(request, user)
            if next_url and url_has_allowed_host_and_scheme(
                    next_url, {request.get_host()}, request.is_secure()):
                return redirect(next_url)
            return redirect('myfeeds')
    else:
        form = LoginForm(request)

    return render(request, 'registration/login.html',
                  {'form': form, 'next': next_url})


def logout_view(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    auth_logout(request)
    return redirect('index')


def _json_error(message, status=400, captcha=False):
    payload = {'error': message}
    if captcha:
        payload['captcha'] = True
    return HttpResponse(json.dumps(payload), status=status,
                        content_type='application/json')


def _request_payload(request):
    if request.method != 'POST':
        return request.GET
    if 'application/json' in (request.content_type or ''):
        try:
            payload = json.loads(request.body or b'{}')
        except (TypeError, ValueError):
            return None
        return payload if isinstance(payload, dict) else None
    return request.POST


def _discover_url(payload):
    raw_url = payload.get('url')
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise _BadRequest('Url is required')
    try:
        url = _normalize_discovery_url(raw_url.strip())
    except ValueError as exc:
        raise _BadRequest('Invalid url') from exc
    form_data = payload.copy()
    form_data['url'] = url
    form = IndexForm(form_data)
    if not form.is_valid():
        if form.errors.get('captcha'):
            raise _BadRequest(str(form.errors['captcha'][0]), captcha=True)
        raise _BadRequest('Invalid url')
    return url


def _bad_request_response(exc):
    if exc.captcha:
        return _json_error(exc.message, captcha=True)
    return HttpResponseBadRequest(exc.message, content_type='text/plain')


def discover(request):
    """Proxy feed discovery to the downloader after a captcha check."""
    if request.method not in ('GET', 'POST'):
        return HttpResponseNotAllowed(['GET', 'POST'])
    payload = _request_payload(request)
    if payload is None:
        return HttpResponseBadRequest('Invalid JSON body')
    try:
        url = _discover_url(payload)
    except _BadRequest as exc:
        return _bad_request_response(exc)

    target = DOWNLOADER_BASE_URL.rstrip('/') + '/discover?' + urllib.parse.urlencode({'url': url})
    try:
        with urllib.request.urlopen(target, timeout=35) as response:  # nosec B310
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        return HttpResponse(exc.read(), status=exc.code,
                            content_type='application/json')
    except (urllib.error.URLError, OSError, ValueError):
        return _json_error('Feed discovery failed', status=502)
    return HttpResponse(body, status=status, content_type='application/json')
