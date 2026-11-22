from datetime import timezone

import pytest

from pol.reader.errors import ParseError
from pol.reader.parse import (
    absolutize,
    html_to_text,
    parse_date,
    page_image,
    parse_feed,
    sanitize_html,
    strip_links,
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


def test_extensionless_media_thumbnail_is_used_as_an_image():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel><title>T</title><link>https://example.com/</link>
    <item><title>A</title><link>https://example.com/a</link>
      <media:content url="https://cdn.example.com/clip" type="video/mp4">
        <media:thumbnail url="https://cdn.example.com/thumb/42"/>
      </media:content>
    </item>
    <item><title>B</title><link>https://example.com/b</link>
      <media:content url="https://cdn.example.com/hero" medium="image"/>
    </item>
  </channel>
</rss>"""
    feed = parse_feed(xml.encode('utf-8'), 'https://example.com/feed.xml')
    assert feed.items[0].images == ['https://cdn.example.com/thumb/42']
    assert feed.items[1].images == ['https://cdn.example.com/hero']


def test_lazy_loaded_image_falls_back_to_data_src():
    item = _item_with_description(
        '<img src="data:image/gif;base64,AAAA" data-src="/photo.jpg">')
    assert item.images == ['https://example.com/photo.jpg']


def test_sanitize_escapes_text_that_looks_like_markup():
    cleaned = sanitize_html('<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>')
    assert '<script>' not in cleaned
    assert '&lt;script&gt;' in cleaned


def test_sanitize_keeps_text_after_a_dropped_element():
    cleaned = sanitize_html('<p>before<script>x()</script>after</p>')
    assert '<script' not in cleaned
    assert 'before' in cleaned and 'after' in cleaned
def test_parse_iso_8859_1_declared_feed_keeps_text():
    raw = ('<?xml version="1.0" encoding="iso-8859-1"?>'
           '<rss><channel><title>café</title>'
           '<item><title>café</title><link>https://example.com/a</link></item>'
           '</channel></rss>').encode('iso-8859-1')
    feed = parse_feed(raw, 'https://example.com/feed')
    assert feed.title == 'café'
    assert feed.items[0].title == 'café'


def test_parse_utf16_feed_keeps_text():
    raw = ('<?xml version="1.0" encoding="utf-16"?>'
           '<rss><channel><title>café</title>'
           '<item><title>café</title><link>https://example.com/a</link></item>'
           '</channel></rss>').encode('utf-16')
    feed = parse_feed(raw, 'https://example.com/feed')
    assert feed.title == 'café'
    assert feed.items[0].title == 'café'


def test_rss_prefers_dc_creator_over_email_author():
    raw = """<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
    <channel><title>T</title><item><title>I</title><link>https://example.com/i</link>
    <author>alice@example.com</author><dc:creator>Alice</dc:creator></item></channel></rss>"""
    feed = parse_feed(raw, 'https://example.com/feed')
    assert feed.items[0].author == 'Alice'


def test_guid_is_permalink_false_is_not_used_as_link():
    raw = """<rss version="2.0"><channel><title>T</title><item><title>I</title>
    <guid isPermaLink="false">urn:post:1</guid></item></channel></rss>"""
    feed = parse_feed(raw, 'https://example.com/feed')
    assert feed.items[0].link == ''
    assert feed.items[0].id == 'urn:post:1'


def test_json_feed_content_text_is_escaped():
    raw = """{"version":"https://jsonfeed.org/version/1.1","title":"T","items":[
    {"id":"1","content_text":"<b>plain</b>","summary":"<i>sum</i>"}]}"""
    feed = parse_feed(raw.encode(), 'https://example.com/feed.json')
    assert feed.items[0].content == '&lt;b&gt;plain&lt;/b&gt;'
    assert feed.items[0].summary == '&lt;i&gt;sum&lt;/i&gt;'


def test_json_feed_image_is_preserved():
    raw = """{"version":"https://jsonfeed.org/version/1.1","title":"T","items":[
    {"id":"1","image":"https://example.com/i.jpg","content_html":"<p>x</p>"}]}"""
    feed = parse_feed(raw.encode(), 'https://example.com/feed.json')
    assert feed.items[0].images[0] == 'https://example.com/i.jpg'


def test_json_feed_rejects_non_list_items():
    with pytest.raises(ParseError):
        parse_feed(b'{"version":"https://jsonfeed.org/version/1.1","items":42}',
                   'https://example.com/feed.json')


def test_sanitize_html_escapes_text_nodes():
    result = sanitize_html('&lt;img src=x onerror=alert(1)&gt;<b>ok</b>')
    assert '<img' not in result
    assert '&lt;img' in result
    assert '<b>ok</b>' in result


def test_sanitize_html_preserves_text_after_removed_embed():
    result = sanitize_html('<p>before</p><iframe src="x"></iframe>after')
    assert 'before' in result
    assert 'after' in result
    assert '<iframe' not in result


def test_media_content_file_size_becomes_the_enclosure_length():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel><title>T</title><link>https://example.com/</link>
    <item><title>A</title><link>https://example.com/a</link>
      <media:content url="https://example.com/clip.mp4" type="video/mp4" fileSize="2048"/>
    </item>
  </channel>
</rss>"""
    item = parse_feed(xml.encode('utf-8'), 'https://example.com/feed.xml').items[0]
    assert item.enclosures[0]['length'] == '2048'


def test_json_feed_keeps_content_text_when_html_is_empty():
    payload = ('{"version": "https://jsonfeed.org/version/1.1", "title": "T",'
               ' "items": [{"id": "1", "content_html": "", "content_text": "Tom & Jerry"}]}')
    feed = parse_feed(payload.encode('utf-8'), 'https://example.com/feed.json')
    assert 'Tom' in feed.items[0].content
    assert html_to_text(feed.items[0].content) == 'Tom & Jerry'


def test_html_to_text_keeps_a_plain_ampersand_word():
    assert html_to_text('see https://example.com/?a=1&copy=2') == 'see https://example.com/?a=1&copy=2'
    assert html_to_text('Tom &amp; Jerry') == 'Tom & Jerry'


def test_html_to_text_decodes_named_entities_that_end_with_a_semicolon():
    # Whitespace is normalised, so &nbsp; becomes a plain space.
    assert html_to_text('a&nbsp;b &copy; 2026') == 'a b \u00a9 2026'
    assert html_to_text('keep &copy= literal') == 'keep &copy= literal'


def test_html_to_text_leaves_unknown_entity_names_alone():
    assert html_to_text('&copyright; 2026') == '&copyright; 2026'


def test_html_to_text_decodes_numeric_references():
    assert html_to_text("it&#x27;s &amp; fine") == "it's & fine"


def test_page_image_prefers_open_graph():
    html = ('<html><head><meta property="og:image" content="/hero.jpg"></head>'
            '<body><img src="/small.png"></body></html>')
    assert page_image(html, 'https://example.com/article') == 'https://example.com/hero.jpg'


def test_page_image_falls_back_to_large_img():
    html = ('<html><body><img src="/logo.svg">'
            '<img src="/hero.jpg" width="1200" height="630"></body></html>')
    assert page_image(html, 'https://example.com/article') == 'https://example.com/hero.jpg'


def test_page_image_ignores_data_and_svg():
    html = ('<html><body><img src="data:image/png;base64,x">'
            '<img src="/icon.svg"></body></html>')
    assert page_image(html, 'https://example.com/article') == ''


def test_rss_prefers_feedburner_orig_link():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:feedburner="http://rssnamespace.org/feedburner/ext/1.0">
  <channel>
    <title>Burner</title>
    <item>
      <title>Post</title>
      <link>https://feedproxy.example/~r/site/~3/abc</link>
      <feedburner:origLink>https://example.com/real-post</feedburner:origLink>
    </item>
  </channel>
</rss>"""
    feed = parse_feed(xml, 'https://feedproxy.example/site')
    assert feed.items[0].link == 'https://example.com/real-post'


def test_strip_links_keeps_the_text():
    result = strip_links('<p>see <a href="/x">this</a> and <a href="/y">that</a></p>')
    assert '<a' not in result
    assert 'see this and that' in result
