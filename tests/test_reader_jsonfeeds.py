import json

from pol.reader.jsonfeeds import Rules, load_rules, parse_custom, rules_for_url
from pol.reader.parse import parse_feed

JSON_DOC = {
    'feed': {'title': 'API feed', 'link': 'https://example.com/'},
    'data': {
        'posts': [
            {'title': 'One', 'url': '/one', 'body': '<p>First</p>',
             'created': '2026-11-21T10:00:00Z', 'author': 'A', 'image': '/one.jpg'},
            {'title': 'Two', 'url': 'https://example.com/two', 'body': '<p>Second</p>'},
        ]
    },
}


def test_json_rules_dotted_paths_and_wildcard():
    rules = Rules.from_mapping({
        'mode': 'json',
        'title': 'feed.title',
        'link': 'feed.link',
        'items': 'data.posts[]',
        'item_title': 'title',
        'item_link': 'url',
        'item_content': 'body',
        'item_time': 'created',
        'item_author': 'author',
        'item_image': 'image',
    })
    feed = parse_custom(json.dumps(JSON_DOC), 'https://example.com/api', rules)
    assert feed.title == 'API feed'
    assert [item.title for item in feed.items] == ['One', 'Two']
    assert feed.items[0].link == 'https://example.com/one'
    assert feed.items[0].date.year == 2026
    assert feed.items[0].images == ['https://example.com/one.jpg']


def test_json_feed_falls_back_to_standard_parser():
    doc = json.dumps({
        'version': 'https://jsonfeed.org/version/1.1',
        'title': 'Standard',
        'items': [{'id': '1', 'title': 'X', 'content_html': '<p>x</p>'}],
    })
    feed = parse_feed(doc.encode(), 'https://example.com/feed.json')
    assert feed.title == 'Standard'
    assert feed.items[0].title == 'X'


def test_html_xpath_rules_with_class_shorthand():
    page = """
    <html><body>
      <div class="card"><h2><a href="/a">A</a></h2><div class="body"><p>Alpha</p></div></div>
      <div class="card"><h2><a href="/b">B</a></h2><div class="body"><p>Beta</p></div></div>
    </body></html>
    """
    rules = Rules.from_mapping({
        'mode': 'html',
        'items': '//div[class=card]',
        'item_title': './/h2/a/text()',
        'item_link': './/h2/a/@href',
        'item_content': './/div[class=body]',
    })
    feed = parse_custom(page, 'https://example.com/list', rules)
    assert [item.title for item in feed.items] == ['A', 'B']
    assert feed.items[0].link == 'https://example.com/a'
    assert '<p>Alpha</p>' in feed.items[0].content


def test_xml_mode_rules():
    xml = """<root><item><title>X</title><link>/x</link><body>Body</body></item></root>"""
    rules = Rules.from_mapping({
        'mode': 'xml',
        'items': '//item',
        'item_title': 'title',
        'item_link': 'link',
        'item_content': 'body',
    })
    feed = parse_custom(xml, 'https://example.com/x', rules)
    assert feed.items[0].title == 'X'
    assert feed.items[0].content == 'Body'


def test_load_rules_from_json_and_ini(tmp_path):
    json_path = tmp_path / 'rules.json'
    json_path.write_text(json.dumps({
        'api': {'mode': 'json', 'items': 'data.posts[]', 'item_title': 'title'},
    }), encoding='utf-8')
    rules = load_rules(str(json_path))
    assert rules['api'].items == 'data.posts[]'

    ini_path = tmp_path / 'rules.ini'
    ini_path.write_text('[page]\nmode = html\nitems = //li\nitem_title = a\n', encoding='utf-8')
    rules = load_rules(str(ini_path))
    assert rules['page'].mode == 'html'
    assert rules['page'].item_title == 'a'


def test_rules_for_url_uses_path_patterns():
    rules = {
        'api': Rules.from_mapping({'mode': 'json', 'path': 'https://api.example.com/*'}),
    }
    assert rules_for_url(rules, 'https://api.example.com/v1') is rules['api']
    assert rules_for_url(rules, 'https://other.example.com/') is None


def test_json_rules_accept_star_wildcard():
    rules = Rules.from_mapping({
        'mode': 'json',
        'items': 'data.posts[*]',
        'item_title': 'title',
        'item_link': 'url',
    })
    feed = parse_custom(json.dumps(JSON_DOC), 'https://example.com/api', rules)
    assert [item.title for item in feed.items] == ['One', 'Two']


def test_xml_mode_strips_encoding_declaration():
    xml = ('<?xml version="1.0" encoding="iso-8859-1"?>'
           '<root><item><title>café</title><link>/x</link></item></root>').encode('iso-8859-1')
    rules = Rules.from_mapping({
        'mode': 'xml',
        'items': '//item',
        'item_title': 'title',
        'item_link': 'link',
    })
    feed = parse_custom(xml, 'https://example.com/x', rules)
    assert feed.items[0].title == 'café'
