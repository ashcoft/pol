"""Tests for the date and image selectors of the feed builder."""

import datetime
import os

import django
from lxml import etree
from lxml import html as lxml_html
from scrapy.selector import Selector

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'frontend.frontend.settings')
django.setup()

from frontend.frontend.views import (  # noqa: E402
    _get_date_xpath,
    _get_image_xpath,
    _get_link_xpath,
    _xpath_base,
)
from pol.feed import (  # noqa: E402
    Feed,
    _as_utc,
    _image_mime,
    _legacy_normalize_images,
    _normalize_images,
    _parse_date,
    _sanitize_srcset,
    _sanitize_urls,
    _usable_url,
    _xml_text,
)


def test_parse_date_accepts_common_formats():
    assert _parse_date('November 20, 2026').date() == datetime.date(2026, 11, 20)
    assert _parse_date('2026-11-19').date() == datetime.date(2026, 11, 19)
    assert _parse_date('<span>20 Nov 2026</span>').date() == datetime.date(2026, 11, 20)


def test_parse_date_returns_none_for_unusable_values():
    assert _parse_date('') is None
    assert _parse_date(None) is None
    assert _parse_date('not a date') is None
    # No year: dateutil would fill it with the current one, giving an
    # unchanged article a new date on every refresh.
    assert _parse_date('12:30') is None
    assert _parse_date('20 Nov') is None
    assert _parse_date('November 2026') is None
    assert _parse_date('2026') is None
    assert _parse_date('2026-11') is None


def test_as_utc_normalizes_naive_and_aware_values():
    naive = datetime.datetime(2026, 11, 20, 12, 0)
    assert _as_utc(naive) == naive.replace(tzinfo=datetime.timezone.utc)
    aware = datetime.datetime(2026, 11, 20, 12, 0,
                             tzinfo=datetime.timezone(datetime.timedelta(hours=3)))
    assert _as_utc(aware) == datetime.datetime(2026, 11, 20, 9, 0, tzinfo=datetime.timezone.utc)
    assert _as_utc(None) is None


def test_parse_date_accepts_two_digit_years():
    assert _parse_date('20 Nov 26').date() == datetime.date(2026, 11, 20)


def test_date_xpath_prefers_datetime_and_keeps_all_children():
    with_datetime = Selector(
        text='<html><body><time datetime="2026-11-19T10:00:00Z">Yesterday</time></body></html>'
    ).xpath('//body')
    assert with_datetime.xpath(
        _get_date_xpath('time[1]/child::node()')).extract() == ['2026-11-19T10:00:00Z']

    label = Selector(
        text='<html><body><time><span>20</span> Nov 2026</time></body></html>'
    ).xpath('//body')
    values = label.xpath(_get_date_xpath('time[1]/child::node()')).extract()
    assert ''.join(values) == '<span>20</span> Nov 2026'

    empty_attribute = Selector(
        text='<html><body><time datetime="">20 Nov 2026</time></body></html>'
    ).xpath('//body')
    assert ''.join(empty_attribute.xpath(
        _get_date_xpath('time[1]/child::node()')).extract()) == '20 Nov 2026'


def test_date_xpath_is_valid_when_date_is_the_item():
    # A bare '.' cannot take a predicate in XPath 1.0.
    xpath = _get_date_xpath('./child::node()')
    assert '.[' not in xpath

    node = Selector(
        text='<html><body><time datetime="2026-11-19T10:00:00Z">Yesterday</time></body></html>'
    ).xpath('//time')
    assert node.xpath(xpath).extract() == ['2026-11-19T10:00:00Z']

    label = Selector(
        text='<html><body><time><span>20</span> Nov 2026</time></body></html>'
    ).xpath('//time')
    assert ''.join(label.xpath(xpath).extract()) == '<span>20</span> Nov 2026'


def test_xpath_base_only_strips_generated_suffix():
    assert _xpath_base('img[1]/child::node()') == 'img[1]'
    assert _xpath_base('./child::node()') == '.'
    assert _xpath_base('.//img/@src') == './/img/@src'


def test_image_xpath_keeps_element_path():
    assert _get_image_xpath('img[1]/child::node()') == 'img[1]'
    assert _get_image_xpath('.//img/@src') == './/img/@src'


def test_extract_image_prefers_lazy_attribute_over_src():
    feed = Feed({})
    node = Selector(text='<article><img data-src="/real.png" src="/blank.gif"></article>').xpath('//article')
    assert feed._extract_image(node, 'img[1]') == '/real.png'


def test_extract_image_skips_data_uri_case_insensitively():
    feed = Feed({})
    node = Selector(
        text='<article><img src="DATA:image/png;base64,AAA" data-src="/real.png"></article>'
    ).xpath('//article')
    assert feed._extract_image(node, 'img[1]') == '/real.png'

    only_placeholder = Selector(
        text='<article><img src="DATA:image/png;base64,AAA"></article>'
    ).xpath('//article')
    assert feed._extract_image(only_placeholder, 'img[1]') is None


def test_extract_image_accepts_attribute_selector():
    feed = Feed({})
    node = Selector(text='<article><img src="/plain.png"></article>').xpath('//article')
    assert feed._extract_image(node, 'img[1]/@src') == '/plain.png'
    assert feed._extract_image(node, 'img[1]/child::node()') is None


def test_link_xpath_handles_nested_and_wrapping_anchors():
    nested = lxml_html.fromstring('<html><body><h2><a href="/nested">T</a></h2></body></html>')
    assert nested.xpath('//body')[0].xpath(_get_link_xpath('h2[1]/child::node()')) == ['/nested']

    wrapping = lxml_html.fromstring('<html><body><a href="/wrapping"><span>T</span></a></body></html>')
    assert wrapping.xpath('//body')[0].xpath(
        _get_link_xpath('a[1]/span[1]/child::node()')) == ['/wrapping']


def test_normalize_images_keeps_surrounding_text():
    out = _normalize_images('Summary <img src="thumb.png"> tail', 'https://example.com/a/b')
    assert out.startswith('Summary ')
    assert 'src="https://example.com/a/thumb.png"' in out
    assert out.endswith(' tail')


def test_image_mime_guesses_from_extension():
    assert _image_mime('https://example.com/a.png') == 'image/png'
    assert _image_mime('https://example.com/a.webp') == 'image/webp'
    assert _image_mime('https://example.com/a.png?v=1') == 'image/png'
    assert _image_mime('https://example.com/a') == 'image/jpeg'


def test_extract_image_uses_later_image_after_placeholder():
    feed = Feed({})
    node = Selector(
        text='<article><img src="data:image/png;base64,AAA"><img src="/real.png"></article>'
    ).xpath('//article')
    assert feed._extract_image(node, 'img') == '/real.png'


def test_usable_image_rejects_non_http_schemes():
    assert Feed._usable_image('https://example.com/a.png')
    assert Feed._usable_image('/img/a.png')
    assert Feed._usable_image('//cdn.example.com/a.png')
    assert not Feed._usable_image('javascript:alert(1)')
    assert not Feed._usable_image('file:///etc/passwd')
    assert not Feed._usable_image('data:image/png;base64,AAA')
    assert not Feed._usable_image('http://[::1')


def test_xml_text_drops_characters_xml_cannot_represent():
    assert _xml_text('a\x00b\x0bc\ud800d') == 'abcd'
    assert _xml_text(None) == ''


def test_usable_url_keeps_web_and_relative_urls_only():
    assert _usable_url('https://example.com/a.png')
    assert _usable_url('/img/a.png')
    assert _usable_url('//cdn.example.com/a.png')
    assert _usable_url('pic.png')
    assert not _usable_url('file:///etc/passwd')
    assert not _usable_url('javascript:alert(1)')
    assert not _usable_url('data:image/png;base64,AAA')
    assert not _usable_url('vbscript:msgbox(1)')


def test_sanitize_urls_drops_local_and_script_urls():
    cleaned = _sanitize_urls(
        '<a href="javascript:alert(1)">x</a>'
        '<img src="file:///etc/passwd">'
        '<img src="https://example.com/ok.png">'
        '<img srcset="file:///a.png 1x, https://example.com/b.png 2x">'
        '<div onclick="alert(1)">y</div>'
    )
    assert 'javascript:' not in cleaned
    assert 'file:///' not in cleaned
    assert 'https://example.com/ok.png' in cleaned
    assert 'https://example.com/b.png 2x' in cleaned
    assert 'onclick' not in cleaned


def _build_feed(monkeypatch, page, required_link=True, include_link=True):
    feed = Feed({})
    monkeypatch.setattr(feed, 'fill_time', lambda feed_id, items: 0)
    fields = {
        'title': 'h2/a/text()',
        'description': 'div[@class="desc"]',
        'image': 'img[1]/@src',
    }
    required = {'title': True, 'description': True, 'image': False}
    if include_link:
        fields['link'] = 'h2/a/@href'
        required['link'] = required_link
    config = {
        'id': 1,
        'uri': 'https://example.com/blog/',
        'xpath': '//article',
        'fields': fields,
        'required': required,
    }
    return feed.buildFeed(Selector(text=page), page, config)


def test_build_feed_drops_invalid_xml_characters(monkeypatch):
    page = (
        '<html><head><title>AT&amp;T</title></head><body><article>'
        '<h2><a href="/post">Tom &amp; Jerry</a></h2>'
        '<div class="desc">bad\x0btext</div>'
        '</article></body></html>'
    )
    xml, count, _new = _build_feed(monkeypatch, page)
    assert count == 1
    root = etree.fromstring(xml.encode('utf-8'))
    description = root.find('.//item/description').text
    assert 'badtext' in description


def test_build_feed_drops_unsafe_image_urls(monkeypatch):
    page = (
        '<html><head><title>Feed</title></head><body><article>'
        '<h2><a href="/post">Post</a></h2>'
        '<div class="desc">Body <a href="javascript:alert(1)">x</a></div>'
        '<img src="file:///etc/passwd">'
        '</article></body></html>'
    )
    xml, count, _new = _build_feed(monkeypatch, page)
    assert count == 1
    assert 'file:///' not in xml
    assert 'javascript:' not in xml
    assert '<enclosure' not in xml


def test_build_feed_survives_a_malformed_link(monkeypatch):
    page = (
        '<html><head><title>Feed</title></head><body><article>'
        '<h2><a href="http://[bad">Post</a></h2>'
        '<div class="desc">Body</div>'
        '</article></body></html>'
    )
    xml, count, _new = _build_feed(monkeypatch, page, required_link=False)
    assert count == 1
    etree.fromstring(xml.encode('utf-8'))


def test_usable_url_rejects_control_characters_in_scheme():
    assert not _usable_url('java\tscript:alert(1)')
    assert not _usable_url('java\nscript:alert(1)')
    assert not _usable_url('java\rscript:alert(1)')
    assert not _usable_url(' javascript:alert(1)')


def test_sanitize_urls_escapes_leading_text():
    cleaned = _sanitize_urls(
        '&lt;img src=x onerror=alert(1)&gt;'
        '<a href="javascript:alert(2)">x</a>'
    )
    assert '<img src=x' not in cleaned
    assert '&lt;img src=x' in cleaned


def test_normalize_images_escapes_leading_text():
    out = _normalize_images(
        '&lt;img src=x onerror=alert(1)&gt;<img src="thumb.png">',
        'https://example.com/a/'
    )
    assert '<img src=x' not in out
    assert '&lt;img src=x' in out


def test_legacy_image_normalization_is_kept_for_guids():
    raw = '<img src="file:///etc/passwd" loading="lazy">'
    assert 'loading' in _legacy_normalize_images(raw, 'https://example.com/')
    assert 'loading' not in _normalize_images(raw, 'https://example.com/')


def test_sanitize_srcset_keeps_commas_inside_urls():
    cleaned = _sanitize_srcset(
        'https://cdn.example/cdn-cgi/image/width=320,quality=80/photo.jpg 1x, '
        'file:///etc/passwd 2x, https://example.com/b.png 2x'
    )
    assert 'width=320,quality=80/photo.jpg 1x' in cleaned
    assert 'https://example.com/b.png 2x' in cleaned
    assert 'file:///' not in cleaned


def test_build_link_resolves_relative_urls_with_a_malformed_page_base():
    feed = Feed({})
    html = '<html><head><base href="http://[bad"></head><body></body></html>'
    assert feed._build_link(html, 'https://example.com/blog/post', '/img/a.png') == \
        'https://example.com/img/a.png'


def test_linkless_guid_ignores_sanitizer_only_changes(monkeypatch):
    page = (
        '<html><head><title>Feed</title></head><body><article>'
        '<h2><a href="/post">Post</a></h2>'
        '<div class="desc">Contact <a href="mailto:editor@example.com">us</a></div>'
        '</article></body></html>'
    )
    normal, count, _new = _build_feed(monkeypatch, page, include_link=False)
    assert count == 1
    normal_guid = etree.fromstring(normal.encode('utf-8')).find('.//item/guid').text

    monkeypatch.setattr('pol.feed._sanitize_urls', lambda fragment: fragment)
    unsanitized, count, _new = _build_feed(monkeypatch, page, include_link=False)
    assert count == 1
    unsanitized_guid = etree.fromstring(
        unsanitized.encode('utf-8')).find('.//item/guid').text

    assert normal_guid == unsanitized_guid
