"""Tests for the date and image selectors of the feed builder."""

import datetime
import os

import django
from lxml import html as lxml_html
from scrapy.selector import Selector

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'frontend.frontend.settings')
django.setup()

from frontend.frontend.views import (  # noqa: E402
    _get_image_xpath,
    _get_link_xpath,
    _xpath_base,
)
from pol.feed import (  # noqa: E402
    Feed,
    _as_utc,
    _image_mime,
    _normalize_images,
    _parse_date,
)


def test_parse_date_accepts_common_formats():
    assert _parse_date('November 20, 2026').date() == datetime.date(2026, 11, 20)
    assert _parse_date('2026-11-19').date() == datetime.date(2026, 11, 19)
    assert _parse_date('<span>20 Nov 2026</span>').date() == datetime.date(2026, 11, 20)


def test_parse_date_returns_none_for_unusable_values():
    assert _parse_date('') is None
    assert _parse_date(None) is None
    assert _parse_date('not a date') is None


def test_as_utc_normalizes_naive_and_aware_values():
    naive = datetime.datetime(2026, 11, 20, 12, 0)
    assert _as_utc(naive).tzinfo is datetime.timezone.utc
    aware = datetime.datetime(2026, 11, 20, 12, 0,
                             tzinfo=datetime.timezone(datetime.timedelta(hours=3)))
    assert _as_utc(aware) == datetime.datetime(2026, 11, 20, 9, 0, tzinfo=datetime.timezone.utc)
    assert _as_utc(None) is None


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
    assert _image_mime('https://example.com/a') == 'image/jpeg'
