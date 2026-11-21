import json

from pol.reader.cli import main

from .conftest import RSS_FEED


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
