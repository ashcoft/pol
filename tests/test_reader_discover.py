from pol.reader.discover import common_candidates, discover_from_html, find_feeds
from pol.reader.http import Fetcher

from .conftest import RSS_FEED


def test_discover_from_html_links_and_anchors():
    page = """
    <html><head>
      <link rel="alternate" type="application/rss+xml" title="Main" href="/feed.xml">
      <link rel="stylesheet" href="/style.css">
    </head><body>
      <a href="/atom.xml">Atom</a>
      <a href="/feedback">Feedback</a>
      <a href="mailto:x@example.com">Mail</a>
    </body></html>
    """
    refs = discover_from_html(page, 'https://example.com/blog/post')
    urls = [ref.url for ref in refs]
    assert 'https://example.com/feed.xml' in urls
    assert 'https://example.com/atom.xml' in urls
    assert all('feedback' not in url for url in urls)
    assert all('mailto' not in url for url in urls)
    assert refs[0].title == 'Main'
    assert refs[0].type == 'application/rss+xml'


def test_discover_deduplicates():
    page = '<link rel="alternate" type="application/rss+xml" href="/feed"><a href="/feed">RSS</a>'
    refs = discover_from_html(page, 'https://example.com/')
    assert len(refs) == 1


def test_common_candidates_same_origin():
    refs = common_candidates('https://example.com/blog/post')
    urls = {ref.url for ref in refs}
    assert 'https://example.com/feed' in urls
    assert 'https://example.com/rss.xml' in urls
    assert all(url.startswith('https://example.com/') for url in urls)


def test_find_feeds_on_page(http_server):
    http_server.routes.update({
        '/': (200, {'Content-Type': 'text/html'}, """
            <html><head><link rel="alternate" type="application/rss+xml" href="/feed.xml"></head>
            <body>hello</body></html>"""),
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
    })

    refs = find_feeds(http_server.base_url + '/')
    assert len(refs) == 1
    assert refs[0].url == http_server.base_url + '/feed.xml'
    assert refs[0].title == 'Example feed'
    assert refs[0].type == 'application/rss+xml'


def test_find_feeds_accepts_a_direct_feed(http_server):
    http_server.routes['/feed.xml'] = (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED)
    refs = find_feeds(http_server.base_url + '/feed.xml')
    assert len(refs) == 1
    assert refs[0].source == 'direct'


def test_find_feeds_verifies_candidates(http_server):
    http_server.routes.update({
        '/': (200, {'Content-Type': 'text/html'},
              '<link rel="alternate" type="application/rss+xml" href="/dead.xml">'),
        '/dead.xml': (404, {'Content-Type': 'text/plain'}, 'gone'),
    })
    refs = find_feeds(http_server.base_url + '/')
    assert refs == []


def test_find_feeds_uses_well_known_paths(http_server):
    http_server.routes.update({
        '/': (200, {'Content-Type': 'text/html'}, '<html><body>no links</body></html>'),
        '/feed': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
    })
    refs = find_feeds(http_server.base_url + '/')
    assert [ref.url for ref in refs] == [http_server.base_url + '/feed']


def test_find_feeds_with_injected_fetcher(http_server):
    http_server.routes['/'] = (200, {'Content-Type': 'text/html'}, '<html></html>')
    fetcher = Fetcher(timeout=5)
    refs = find_feeds(http_server.base_url + '/', fetcher=fetcher, verify=False)
    assert refs  # common candidates, unverified
