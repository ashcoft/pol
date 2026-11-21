import json
from datetime import datetime, timezone

import pytest

from pol.reader.model import Feed, Item
from pol.reader.output import format_feed, to_csv, to_html, to_json, to_rss


def _feed():
    return Feed(
        title='Example & Co',
        link='https://example.com/',
        description='Desc',
        language='en',
        url='https://example.com/feed',
        items=[
            Item(
                title='A <post>',
                link='https://example.com/a',
                id='a',
                summary='<p>Summary</p>',
                content='<p>Full <b>body</b></p>',
                date=datetime(2026, 11, 21, 10, tzinfo=timezone.utc),
                author='Alice',
                images=['https://example.com/a.jpg'],
                enclosures=[{'url': 'https://example.com/a.jpg',
                              'type': 'image/jpeg', 'length': '10'}],
            )
        ],
    )


def test_to_rss_has_items_content_and_enclosure():
    rss = to_rss(_feed())
    assert '<rss' in rss
    assert 'A &lt;post&gt;' in rss
    assert '<content:encoded>' in rss
    assert 'Full <b>body</b>' in rss
    assert '<enclosure' in rss
    assert 'pubDate' in rss
    assert 'dc:creator' in rss


def test_to_json_is_json_feed():
    data = json.loads(to_json(_feed()))
    assert data['version'] == 'https://jsonfeed.org/version/1.1'
    assert data['title'] == 'Example & Co'
    assert data['items'][0]['content_html'].startswith('<p>Full')
    assert data['items'][0]['date_published'] == '2026-11-21T10:00:00Z'
    assert data['items'][0]['attachments'][0]['mime_type'] == 'image/jpeg'


def test_to_csv_has_header_and_row():
    rows = to_csv(_feed()).splitlines()
    assert rows[0] == 'title,link,date,author,content'
    assert 'A <post>' in rows[1]
    assert 'Full body' in rows[1]


def test_to_html_escapes_and_sanitizes():
    html = to_html(_feed())
    assert '<!DOCTYPE html>' in html
    assert 'A &lt;post&gt;' in html
    assert '<p>Full <b>body</b></p>' in html


def test_format_feed_content_types():
    assert format_feed(_feed(), 'rss')[1].startswith('application/rss+xml')
    assert format_feed(_feed(), 'json')[1].startswith('application/feed+json')
    assert format_feed(_feed(), 'csv')[1].startswith('text/csv')
    assert format_feed(_feed(), 'html')[1].startswith('text/html')


def test_jsonp_wraps_json():
    body, content_type = format_feed(_feed(), 'jsonp', callback='myCallback')
    assert body.startswith('myCallback({')
    assert body.rstrip().endswith(');')
    assert content_type.startswith('application/javascript')


@pytest.mark.parametrize('callback', ['bad-name', '1abc', 'a(b)'])
def test_jsonp_rejects_invalid_callbacks(callback):
    with pytest.raises(ValueError):
        format_feed(_feed(), 'jsonp', callback=callback)


def test_unknown_format_raises():
    with pytest.raises(ValueError):
        format_feed(_feed(), 'yaml')


def test_html_output_drops_unsafe_link_schemes():
    feed = _feed()
    feed.link = 'javascript:alert(1)'
    feed.items[0].link = 'javascript:alert(2)'
    html = to_html(feed)
    assert 'javascript:' not in html


def test_rss_output_drops_unsafe_link_schemes():
    feed = _feed()
    feed.link = 'javascript:alert(1)'
    feed.items[0].link = 'javascript:alert(2)'
    rss = to_rss(feed)
    assert 'javascript:' not in rss


def test_json_output_drops_unsafe_link_schemes():
    feed = _feed()
    feed.link = 'javascript:alert(1)'
    feed.items[0].link = 'javascript:alert(2)'
    data = json.loads(to_json(feed))
    assert 'home_page_url' not in data
    assert 'url' not in data['items'][0]


def test_csv_neutralizes_formula_cells():
    import csv
    import io

    feed = _feed()
    feed.items[0].title = '=1+1'
    feed.items[0].author = '@cmd'
    feed.items[0].content = '=SUM(A1)'
    rows = list(csv.reader(io.StringIO(to_csv(feed))))
    assert rows[1][0] == "'=1+1"
    assert rows[1][3] == "'@cmd"
    assert rows[1][4] == "'=SUM(A1)"


def test_rss_preserves_cdata_terminator():
    from pol.reader.parse import parse_feed

    feed = _feed()
    feed.items[0].summary = 'a]]>b'
    feed.items[0].content = 'x]]>y'
    parsed = parse_feed(to_rss(feed).encode(), 'https://example.com/feed')
    assert parsed.items[0].summary == 'a]]>b'
    assert parsed.items[0].content == 'x]]>y'


def test_rss_self_link_points_at_the_feed_not_the_homepage():
    data = to_rss(_feed())
    assert 'rel="self"' in data
    assert 'href="https://example.com/feed"' in data
    assert '<link>https://example.com/</link>' in data


def test_rss_export_survives_a_malformed_feed_url():
    feed = _feed()
    feed.url = 'http://[bad/feed'
    data = to_rss(feed)
    assert '<link>https://example.com/</link>' in data
    assert 'rel="self"' not in data
