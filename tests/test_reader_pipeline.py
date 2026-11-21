import json

import pytest

from pol.reader.errors import FetchError, InvalidURLError
from pol.reader.pipeline import Options, process

from .conftest import ARTICLE, RSS_FEED

TRACKING_FEED = RSS_FEED.replace('<link>/article</link>', '<link>/track?utm_source=x</link>')


def test_process_reads_feed_and_fills_fulltext(http_server):
    http_server.routes.update({
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
        '/article': (200, {'Content-Type': 'text/html'}, ARTICLE),
    })

    result = process(http_server.base_url + '/feed.xml',
                     options=Options(format='json', fulltext=True, max_items=5))

    assert result.feed.title == 'Example feed'
    item = result.feed.items[0]
    assert 'full article body' in item.content
    payload = json.loads(result.text)
    assert 'full article body' in payload['items'][0]['content_html']
    assert 'newsletter' not in payload['items'][0]['content_html']


def test_process_proxy_keeps_the_summary(http_server):
    http_server.routes.update({
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
        '/article': (200, {'Content-Type': 'text/html'}, ARTICLE),
    })
    result = process(http_server.base_url + '/feed.xml',
                     options=Options(fulltext=True, proxy=True))
    assert result.feed.items[0].content == ''
    assert result.feed.items[0].summary == '<p>Short summary.</p>'


def test_process_resolves_tracking_links(http_server):
    http_server.routes.update({
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, TRACKING_FEED),
        '/track': (302, {'Location': '/article'}, ''),
        '/article': (200, {'Content-Type': 'text/html'}, ARTICLE),
    })
    result = process(http_server.base_url + '/feed.xml',
                     options=Options(fulltext=False, resolve=True))
    assert result.feed.items[0].link == http_server.base_url + '/article'


def test_process_auto_discovers_a_feed_on_a_page(http_server):
    http_server.routes.update({
        '/': (200, {'Content-Type': 'text/html'},
              '<html><head><link rel="alternate" type="application/rss+xml" href="/feed.xml">'
              '</head><body>blog</body></html>'),
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
    })
    result = process(http_server.base_url + '/', options=Options(fulltext=False))
    assert result.feed.title == 'Example feed'


def test_process_custom_json_rules(http_server):
    doc = {
        'feed': {'title': 'API', 'link': 'https://example.com/'},
        'data': {'posts': [
            {'title': 'One', 'url': '/one', 'body': '<p>First</p>'},
            {'title': 'Two', 'url': '/two', 'body': '<p>Second</p>'},
        ]},
    }
    http_server.routes['/api'] = (200, {'Content-Type': 'application/json'}, json.dumps(doc))

    result = process(http_server.base_url + '/api', options=Options(
        mode='json', items='data.posts[]', item_title='title',
        item_link='url', item_content='body', fulltext=False))

    assert [item.title for item in result.feed.items] == ['One', 'Two']
    assert result.feed.items[0].link == http_server.base_url + '/one'


def test_process_follows_meta_refresh(http_server):
    http_server.routes.update({
        '/': (200, {'Content-Type': 'text/html'},
              '<meta http-equiv="refresh" content="0; url=/feed.xml">'),
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
    })
    result = process(http_server.base_url + '/', options=Options(fulltext=False))
    assert result.feed.title == 'Example feed'


def test_process_reads_gzip_feed(http_server):
    import gzip

    http_server.routes['/feed.xml'] = (
        200, {'Content-Type': 'application/rss+xml', 'Content-Encoding': 'gzip'},
        gzip.compress(RSS_FEED.encode()))
    result = process(http_server.base_url + '/feed.xml', options=Options(fulltext=False))
    assert result.feed.items[0].title == 'First post'


def test_process_search_filter(http_server):
    http_server.routes['/feed.xml'] = (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED)
    assert len(process(http_server.base_url + '/feed.xml',
                       options=Options(fulltext=False, search='First')).feed.items) == 1
    assert len(process(http_server.base_url + '/feed.xml',
                       options=Options(fulltext=False, search='absent')).feed.items) == 0


def test_process_xpath_override(http_server):
    http_server.routes.update({
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
        '/article': (200, {'Content-Type': 'text/html'}, ARTICLE),
    })
    result = process(http_server.base_url + '/feed.xml', options=Options(
        fulltext=True, xpath='//article'))
    assert 'full article body' in result.feed.items[0].content
    assert 'Subscribe' not in result.feed.items[0].content


def test_process_respects_max_items(http_server):
    feed = RSS_FEED.replace('</channel>', """
      <item><title>Second</title><link>/article</link><description>x</description></item>
      <item><title>Third</title><link>/article</link><description>x</description></item>
    </channel>""")
    http_server.routes.update({
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, feed),
        '/article': (200, {'Content-Type': 'text/html'}, ARTICLE),
    })
    result = process(http_server.base_url + '/feed.xml',
                     options=Options(fulltext=True, max_items=1))
    assert result.feed.items[0].content
    assert result.feed.items[1].content == ''


def test_process_rejects_invalid_url():
    with pytest.raises(InvalidURLError):
        process('mailto:x@example.com')


def test_process_raises_on_http_error(http_server):
    http_server.routes['/missing'] = (404, {'Content-Type': 'text/plain'}, 'nope')
    with pytest.raises(FetchError) as excinfo:
        process(http_server.base_url + '/missing')
    assert excinfo.value.status == 404
