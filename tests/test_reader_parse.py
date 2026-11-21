from datetime import timezone

import pytest

from pol.reader.errors import ParseError
from pol.reader.parse import (
    absolutize,
    html_to_text,
    parse_date,
    parse_feed,
    sanitize_html,
)

RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Example</title>
    <link>https://example.com/</link>
    <description>Desc</description>
    <language>en</language>
    <item>
      <title>Post</title>
      <link>https://example.com/post</link>
      <guid>tag:1</guid>
      <description><![CDATA[<p>Summary</p>]]></description>
      <content:encoded><![CDATA[<p>Full <b>body</b></p><img src="/pic.jpg">]]></content:encoded>
      <pubDate>Tue, 21 Nov 2026 10:00:00 GMT</pubDate>
      <dc:creator>Alice</dc:creator>
      <enclosure url="https://example.com/a.mp3" type="audio/mpeg" length="10"/>
    </item>
  </channel>
</rss>
"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom feed</title>
  <subtitle>Sub</subtitle>
  <link rel="alternate" href="https://example.com/"/>
  <entry>
    <title>Entry</title>
    <id>urn:1</id>
    <link rel="alternate" href="https://example.com/entry"/>
    <link rel="enclosure" href="https://example.com/e.jpg" type="image/jpeg"/>
    <summary>Short</summary>
    <content type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml"><p>Full</p></div></content>
    <published>2026-11-21T10:00:00Z</published>
    <author><name>Bob</name></author>
  </entry>
</feed>
"""

RDF = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel><title>RDF feed</title><link>https://example.com/</link></channel>
  <item>
    <title>RDF post</title>
    <link>https://example.com/rdf</link>
    <description>Text</description>
    <dc:date>2026-11-20T08:00:00Z</dc:date>
  </item>
</rdf:RDF>
"""

JSON_FEED = """{
  "version": "https://jsonfeed.org/version/1.1",
  "title": "JSON feed",
  "home_page_url": "https://example.com/",
  "items": [
    {
      "id": "1",
      "url": "https://example.com/j",
      "title": "JSON post",
      "content_html": "<p>Hello</p>",
      "date_published": "2026-11-21T10:00:00Z",
      "authors": [{"name": "Carol"}],
      "attachments": [{"url": "https://example.com/a.png", "mime_type": "image/png", "size_in_bytes": 5}]
    }
  ]
}
"""


def test_parse_rss():
    feed = parse_feed(RSS.encode(), 'https://example.com/feed', 'application/rss+xml')
    assert feed.title == 'Example'
    assert feed.format == 'rss'
    item = feed.items[0]
    assert item.title == 'Post'
    assert item.link == 'https://example.com/post'
    assert 'Full <b>body</b>' in item.content
    assert item.author == 'Alice'
    assert item.date.tzinfo is not None
    assert item.enclosures[0]['url'] == 'https://example.com/a.mp3'
    assert item.images == ['https://example.com/pic.jpg']


def test_parse_atom():
    feed = parse_feed(ATOM.encode(), 'https://example.com/atom')
    assert feed.title == 'Atom feed'
    assert feed.format == 'atom'
    item = feed.items[0]
    assert item.link == 'https://example.com/entry'
    assert '<p>Full</p>' in item.content
    assert item.author == 'Bob'
    assert item.enclosures[0]['type'] == 'image/jpeg'


def test_parse_rdf():
    feed = parse_feed(RDF.encode(), 'https://example.com/rdf')
    assert feed.format == 'rdf'
    assert feed.items[0].title == 'RDF post'
    assert feed.items[0].date.year == 2026


def test_parse_json_feed():
    feed = parse_feed(JSON_FEED.encode(), 'https://example.com/feed.json')
    assert feed.format == 'json'
    assert feed.items[0].title == 'JSON post'
    assert feed.items[0].author == 'Carol'
    assert feed.items[0].enclosures[0]['type'] == 'image/png'


def test_parse_broken_xml_recovers():
    broken = '<rss><channel><title>Broken</title><item><title>X</title><link>https://x</link>'
    feed = parse_feed(broken.encode(), 'https://x')
    assert feed.title == 'Broken'
    assert feed.items[0].title == 'X'


def test_parse_rejects_html():
    with pytest.raises(ParseError):
        parse_feed(b'<html><body><p>not a feed</p></body></html>', 'https://x')


def test_parse_date_formats():
    assert parse_date('Tue, 21 Nov 2026 10:00:00 GMT').tzinfo is not None
    assert parse_date('2026-11-21T10:00:00Z').hour == 10
    assert parse_date('2026-11-21').year == 2026
    assert parse_date('not a date') is None
    assert parse_date(None) is None


def test_absolutize_links_and_lazy_images():
    fragment = '<p><a href="/next">next</a><img data-src="/img.jpg" src="data:placeholder"></p>'
    result = absolutize(fragment, 'https://example.com/a/b')
    assert 'href="https://example.com/next"' in result
    assert 'src="https://example.com/img.jpg"' in result
    assert 'data-src' not in result
    assert 'loading' not in result


def test_sanitize_html_removes_scripts_and_handlers():
    fragment = '<p onclick="evil()">ok</p><script>alert(1)</script><a href="javascript:x">x</a>'
    result = sanitize_html(fragment)
    assert 'script' not in result
    assert 'onclick' not in result
    assert 'javascript:' not in result
    assert 'ok' in result


def test_html_to_text():
    assert html_to_text('<p>Hello&nbsp;<b>world</b></p>') == 'Hello world'


def test_feed_url_defaults_are_kept():
    feed = parse_feed(RSS.encode(), 'https://example.com/feed')
    assert feed.url == 'https://example.com/feed'
    assert feed.items[0].date.tzinfo == timezone.utc


MEDIA_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Media</title>
    <link>https://example.com/</link>
    <item>
      <title>Clip</title>
      <link>https://example.com/clip</link>
      <media:content url="https://example.com/clip.mp4" type="video/mp4">
        <media:thumbnail url="https://example.com/still.jpg"/>
      </media:content>
    </item>
    <item>
      <title>Groups</title>
      <link>https://example.com/groups</link>
      <media:group><media:content url="https://example.com/a.mp4" type="video/mp4"/></media:group>
      <media:group><media:thumbnail url="https://example.com/group.jpg"/></media:group>
    </item>
    <item>
      <title>Params</title>
      <link>https://example.com/params</link>
      <enclosure url="https://example.com/cover.jpg"
                 type="application/octet-stream; name=&quot;cover.jpg&quot;"/>
    </item>
  </channel>
</rss>
"""


def test_nested_and_grouped_media_thumbnails():
    feed = parse_feed(MEDIA_RSS.encode('utf-8'), 'https://example.com/feed.xml')
    assert feed.items[0].images == ['https://example.com/still.jpg']
    assert feed.items[1].images == ['https://example.com/group.jpg']
    assert feed.items[2].images == ['https://example.com/cover.jpg']


def _item_with_description(description):
    xml = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>T</title>
  <item><title>A</title><link>https://example.com/a</link>
    <description><![CDATA[%s]]></description></item>
</channel></rss>""" % description
    return parse_feed(xml.encode('utf-8'), 'https://example.com/feed.xml').items[0]


def test_inline_image_uses_src_not_data_src():
    item = _item_with_description('<img data-src="/placeholder.gif" src="/photo.jpg">')
    assert item.images == ['https://example.com/photo.jpg']


def test_inline_image_accepts_unquoted_src():
    item = _item_with_description('<img src=/photo.jpg?w=800&h=600>')
    assert item.images == ['https://example.com/photo.jpg?w=800&h=600']


def test_inline_image_ignores_escaped_example():
    item = _item_with_description(
        '<code>&lt;img src="/example.png"&gt;</code><img src="/real.png">')
    assert item.images == ['https://example.com/real.png']


def test_inline_image_skips_data_uri():
    item = _item_with_description(
        '<img src="data:image/gif;base64,R0lGOD"><img src="/real.png">')
    assert item.images == ['https://example.com/real.png']


def test_video_enclosure_is_kept_but_not_used_as_an_image():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel><title>T</title><link>https://example.com/</link>
    <item><title>A</title><link>https://example.com/a</link>
      <media:content url="https://example.com/clip.mp4" type="video/mp4"/>
    </item>
  </channel>
</rss>"""
    item = parse_feed(xml.encode('utf-8'), 'https://example.com/feed.xml').items[0]
    assert [enclosure['url'] for enclosure in item.enclosures] == ['https://example.com/clip.mp4']
    assert item.images == []
