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


def test_process_skips_non_http_item_links(http_server):
    feed = RSS_FEED.replace('<link>/article</link>', '<link>mailto:x@example.com</link>')
    http_server.routes['/feed.xml'] = (200, {'Content-Type': 'application/rss+xml'}, feed)
    result = process(http_server.base_url + '/feed.xml',
                     options=Options(fulltext=True, resolve=True))
    assert result.feed.items[0].link == 'mailto:x@example.com'


def test_process_falls_back_after_dead_advertised_feed(http_server):
    http_server.routes.update({
        '/': (200, {'Content-Type': 'text/html'},
              '<link rel="alternate" type="application/rss+xml" href="/old.xml">'),
        '/old.xml': (404, {'Content-Type': 'text/plain'}, 'gone'),
        '/rss.xml': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
    })
    result = process(http_server.base_url + '/', options=Options(fulltext=False))
    assert result.feed.title == 'Example feed'


def _ordered_feed():
    from datetime import datetime, timezone

    from pol.reader.model import Feed, Item

    feed = Feed(title='Ordered', url='https://example.com/feed')
    feed.items = [
        Item(title='old', link='https://example.com/old',
             date=datetime(2026, 11, 20, 10, tzinfo=timezone.utc)),
        Item(title='new', link='https://example.com/new',
             date=datetime(2026, 11, 21, 10, tzinfo=timezone.utc)),
        Item(title='middle', link='https://example.com/middle',
             date=datetime(2026, 11, 20, 12, tzinfo=timezone.utc)),
    ]
    return feed


def test_items_to_process_order_variants():
    from pol.reader.pipeline import _items_to_process

    feed = _ordered_feed()
    titles = lambda items: [item.title for item in items]

    assert titles(_items_to_process(feed, Options(max_items=2, order='first'))) == [
        'old', 'new']
    assert titles(_items_to_process(feed, Options(max_items=2, order='last'))) == [
        'new', 'middle']
    assert titles(_items_to_process(feed, Options(max_items=2, order='newest'))) == [
        'new', 'middle']
    assert titles(_items_to_process(feed, Options(max_items=2, order='oldest'))) == [
        'old', 'middle']
    assert _items_to_process(feed, Options(max_items=0)) == []


def test_fix_items_normalises_titles_and_recovers_links():
    from pol.reader.model import Feed, Item
    from pol.reader.pipeline import _fix_items

    feed = Feed(title='T', url='https://en.wikipedia.org/w/api.php?action=query&feedformat=atom')
    feed.items = [Item(
        title='THIS TITLE IS SHOUTING LOUDLY',
        link='https://translate.google.de/translate?u=https%3A%2F%2Fexample.com%2Farticle',
        summary='<p><b><a href="https://en.wikipedia.org/wiki/Real">Real</a></b></p>',
    )]
    _fix_items(feed, Options())
    assert feed.items[0].title == 'This Title Is Shouting Loudly'
    # The Wikipedia daily-highlight link wins over the wrapper link.
    assert feed.items[0].link == 'https://en.wikipedia.org/wiki/Real'


def test_fix_items_uses_the_reddit_link():
    from pol.reader.model import Feed, Item
    from pol.reader.pipeline import _fix_items

    feed = Feed(title='r/test', url='https://www.reddit.com/r/test/.rss')
    feed.items = [Item(
        title='Post',
        link='https://www.reddit.com/r/test/comments/1/post/',
        content='<p><a href="https://example.com/story">[link]</a></p>',
    )]
    _fix_items(feed, Options())
    assert feed.items[0].link == 'https://example.com/story'


def test_fix_items_unwraps_and_decodes_links():
    from pol.reader.model import Feed, Item
    from pol.reader.pipeline import _fix_items

    feed = Feed(title='T', url='https://example.com/feed')
    feed.items = [
        Item(title='A', link='https://getpocket.com/redirect?url=https%3A%2F%2Fexample.com%2Fa'),
        Item(title='B',
             link='https://feedsportal.com/A0M0example0B0com0C0b/story01.htm'),
    ]
    _fix_items(feed, Options())
    assert feed.items[0].link == 'https://example.com/a'
    assert feed.items[1].link == 'https://example.com/b'
