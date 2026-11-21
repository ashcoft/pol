"""Tests for the date and image selectors of the feed builder."""

import datetime
import os

import django
from lxml import html as lxml_html

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'frontend.frontend.settings')
django.setup()

from frontend.frontend.views import _get_image_xpath, _get_link_xpath  # noqa: E402
from pol.feed import _image_mime, _normalize_images, _parse_date  # noqa: E402


def test_parse_date_accepts_common_formats():
    assert _parse_date('November 20, 2026').date() == datetime.date(2026, 11, 20)
    assert _parse_date('2026-11-19').date() == datetime.date(2026, 11, 19)
    assert _parse_date('<span>20 Nov 2026</span>').date() == datetime.date(2026, 11, 20)


def test_parse_date_returns_none_for_unusable_values():
    assert _parse_date('') is None
    assert _parse_date(None) is None
    assert _parse_date('not a date') is None


def test_image_xpath_finds_real_source_of_lazy_image():
    doc = lxml_html.fromstring(
        '<html><body><article>'
        '<img data-src="/real.png" src="data:image/png;base64,AAA">'
        '</article></body></html>'
    )
    values = doc.xpath('//article')[0].xpath(_get_image_xpath('img[1]/child::node()'))
    assert '/real.png' in values
    # The placeholder is returned too; the feed builder skips data: values.
    assert any(value.startswith('data:') for value in values)


def test_image_xpath_handles_plain_image():
    doc = lxml_html.fromstring('<html><body><article><img src="/plain.png"></article></body></html>')
    assert doc.xpath('//article')[0].xpath(_get_image_xpath('img[1]/child::node()')) == ['/plain.png']


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
