import json

from pol.reader.cli import main

from .conftest import ARTICLE, RSS_FEED


def _serve_feed(http_server):
    http_server.routes['/feed.xml'] = (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED)


def test_cli_outputs_json(http_server, capsys):
    _serve_feed(http_server)
    code = main([http_server.base_url + '/feed.xml', '--no-fulltext', '--format', 'json'])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['title'] == 'Example feed'
    assert payload['items'][0]['title'] == 'First post'


def test_cli_discover(http_server, capsys):
    http_server.routes.update({
        '/': (200, {'Content-Type': 'text/html'},
              '<link rel="alternate" type="application/rss+xml" href="/feed.xml">'),
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'}, RSS_FEED),
    })
    code = main([http_server.base_url + '/', '--discover'])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['feeds'][0]['url'] == http_server.base_url + '/feed.xml'


def test_cli_writes_output_file(http_server, tmp_path, capsys):
    _serve_feed(http_server)
    target = tmp_path / 'feed.json'
    code = main([http_server.base_url + '/feed.xml', '--no-fulltext',
                 '--format', 'json', '-o', str(target)])
    assert code == 0
    assert capsys.readouterr().out == ''
    assert json.loads(target.read_text(encoding='utf-8'))['title'] == 'Example feed'


def test_cli_rejects_invalid_url(capsys):
    code = main(['mailto:x@example.com', '--no-fulltext'])
    assert code == 1
    assert 'error:' in capsys.readouterr().err


def test_cli_returns_error_on_http_failure(http_server, capsys):
    http_server.routes['/missing'] = (404, {'Content-Type': 'text/plain'}, 'nope')
    code = main([http_server.base_url + '/missing', '--no-fulltext'])
    assert code == 1
    assert 'error:' in capsys.readouterr().err


def test_cli_custom_rules_file(http_server, tmp_path, capsys):
    doc = {'data': {'posts': [
        {'title': 'One', 'url': '/one'},
        {'title': 'Two', 'url': '/two'},
    ]}}
    http_server.routes['/api'] = (200, {'Content-Type': 'application/json'}, json.dumps(doc))
    rules = tmp_path / 'rules.json'
    rules.write_text(json.dumps({
        'api': {'mode': 'json', 'items': 'data.posts[]',
                'item_title': 'title', 'item_link': 'url'},
    }), encoding='utf-8')

    code = main([http_server.base_url + '/api', '--rules', str(rules),
                 '--no-fulltext', '--format', 'json'])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert [item['title'] for item in payload['items']] == ['One', 'Two']


CONTENT_FEED = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel><title>Links</title><item>
    <title>Linked</title><link>/article</link>
    <description><![CDATA[<p>Summary</p>]]></description>
    <content:encoded><![CDATA[<p>Read <a href="https://example.com/x">this</a></p>]]></content:encoded>
  </item></channel>
</rss>"""

FIRSTLINK_FEED = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>Pick</title><item>
  <title>Pick</title><link>/wrong</link>
  <description><![CDATA[<p><a href="/right">Right</a></p>]]></description>
</item></channel></rss>"""

ORDERED_FEED = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>Ordered</title>
  <item><title>Old</title><link>/old</link>
    <pubDate>Mon, 20 Nov 2026 10:00:00 GMT</pubDate>
    <description><![CDATA[<p>Old summary.</p>]]></description></item>
  <item><title>New</title><link>/new</link>
    <pubDate>Tue, 21 Nov 2026 10:00:00 GMT</pubDate>
    <description><![CDATA[<p>New summary.</p>]]></description></item>
</channel></rss>"""


def test_cli_posts_the_given_body(http_server, capsys):
    seen = {}

    def route(method, handler):
        length = int(handler.headers.get('Content-Length') or 0)
        seen['method'] = method
        seen['body'] = handler.rfile.read(length) if length else b''
        return 200, {'Content-Type': 'application/rss+xml'}, RSS_FEED

    http_server.routes['/api'] = route
    code = main([http_server.base_url + '/api', '--post', 'q=pol',
                 '--no-fulltext', '--format', 'json'])
    assert code == 0
    assert seen == {'method': 'POST', 'body': b'q=pol'}
    assert json.loads(capsys.readouterr().out)['title'] == 'Example feed'


def test_cli_silent_suppresses_output(http_server, capsys):
    _serve_feed(http_server)
    code = main([http_server.base_url + '/feed.xml', '--no-fulltext', '--silent'])
    assert code == 0
    assert capsys.readouterr().out == ''


def test_cli_noref_drops_item_links(http_server, capsys):
    _serve_feed(http_server)
    code = main([http_server.base_url + '/feed.xml', '--no-fulltext',
                 '--format', 'json', '--noref'])
    assert code == 0
    item = json.loads(capsys.readouterr().out)['items'][0]
    assert 'url' not in item


def test_cli_nolink_strips_anchors_from_content(http_server, capsys):
    http_server.routes['/links.xml'] = (
        200, {'Content-Type': 'application/rss+xml'}, CONTENT_FEED)
    code = main([http_server.base_url + '/links.xml', '--no-fulltext',
                 '--format', 'json', '--nolink'])
    assert code == 0
    content = json.loads(capsys.readouterr().out)['items'][0]['content_html']
    assert '<a' not in content
    assert 'Read this' in content


def test_cli_firstlink_uses_the_first_anchor(http_server, capsys):
    http_server.routes['/pick.xml'] = (
        200, {'Content-Type': 'application/rss+xml'}, FIRSTLINK_FEED)
    code = main([http_server.base_url + '/pick.xml', '--no-fulltext',
                 '--format', 'json', '--firstlink'])
    assert code == 0
    item = json.loads(capsys.readouterr().out)['items'][0]
    assert item['url'].endswith('/right')


def test_cli_order_newest_enriches_the_newest_item(http_server, capsys):
    http_server.routes.update({
        '/ordered.xml': (200, {'Content-Type': 'application/rss+xml'}, ORDERED_FEED),
        '/old': (200, {'Content-Type': 'text/html'}, ARTICLE),
        '/new': (200, {'Content-Type': 'text/html'}, ARTICLE),
    })
    code = main([http_server.base_url + '/ordered.xml', '--format', 'json',
                 '--order', 'newest', '--max-items', '1'])
    assert code == 0
    items = json.loads(capsys.readouterr().out)['items']
    assert 'full article body' not in items[0]['content_html']
    assert 'full article body' in items[1]['content_html']
