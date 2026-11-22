import pytest

from pol.reader.errors import InvalidURLError
from pol.reader.urls import (
    clean_url,
    decode_feedsportal,
    defrag,
    is_http_url,
    looks_like_feed_url,
    normalize_url,
    strip_tracking,
    unwrap_redirector,
)


def test_normalize_url_adds_https_to_bare_hosts():
    assert normalize_url('example.com/path') == 'https://example.com/path'


def test_normalize_url_keeps_http_and_ports():
    assert normalize_url('http://example.com:8080/a') == 'http://example.com:8080/a'
    assert normalize_url('example.com:8080/a') == 'https://example.com:8080/a'


@pytest.mark.parametrize('value', ['', '   ', 'mailto:a@b.c', 'ftp://x.test/f', 'javascript:alert(1)'])
def test_normalize_url_rejects_non_http(value):
    with pytest.raises(InvalidURLError):
        normalize_url(value)


def test_is_http_url():
    assert is_http_url('https://example.com')
    assert not is_http_url('file:///etc/passwd')


def test_strip_tracking_keeps_functional_parameters():
    url = 'https://example.com/a?page=2&utm_source=x&fbclid=y&id=7'
    assert strip_tracking(url) == 'https://example.com/a?page=2&id=7'


def test_unwrap_redirectors():
    assert unwrap_redirector(
        'https://l.facebook.com/l.php?u=https%3A%2F%2Fexample.com%2Fstory') == 'https://example.com/story'
    assert unwrap_redirector(
        'https://www.google.com/url?q=https://example.com/a&sa=D') == 'https://example.com/a'
    assert unwrap_redirector('https://out.reddit.com/x?url=https%3A%2F%2Fexample.com') == 'https://example.com'


def test_unwrap_redirector_leaves_plain_urls_alone():
    url = 'https://example.com/a?u=1'
    assert unwrap_redirector(url) == url


def test_unwrap_redirector_does_not_rewrite_search_queries():
    url = 'https://www.google.com/search?q=cats'
    assert unwrap_redirector(url) == url


def test_strip_tracking_preserves_original_encoding():
    url = 'https://example.com/feed?topic=machine%20learning&utm_source=x&sig=a%2Fb'
    assert strip_tracking(url) == 'https://example.com/feed?topic=machine%20learning&sig=a%2Fb'


def test_clean_url_unwraps_and_removes_fragment():
    url = 'https://l.facebook.com/l.php?u=https%3A%2F%2Fexample.com%2Fa%3Futm_source%3Dx#part'
    assert clean_url(url) == 'https://example.com/a'


def test_defrag():
    assert defrag('https://example.com/a#section') == 'https://example.com/a'


def test_looks_like_feed_url():
    assert looks_like_feed_url('https://example.com/feed')
    assert looks_like_feed_url('https://example.com/rss.xml')
    assert looks_like_feed_url('https://example.com/blog/atom.xml?x=1')
    assert not looks_like_feed_url('https://example.com/about')


def test_unwrap_google_news_pocket_and_translate():
    assert unwrap_redirector(
        'https://translate.google.de/translate?sl=auto&tl=en&u=https%3A%2F%2Fexample.com%2Fa'
    ) == 'https://example.com/a'
    assert unwrap_redirector(
        'https://news.google.com/news/url?sa=t&url=https%3A%2F%2Fexample.com%2Fb'
    ) == 'https://example.com/b'
    assert unwrap_redirector(
        'https://getpocket.com/redirect?url=https%3A%2F%2Fexample.com%2Fc'
    ) == 'https://example.com/c'
    assert unwrap_redirector(
        'https://www.google.co.uk/url?q=https://example.com/d'
    ) == 'https://example.com/d'


def test_unwrap_does_not_touch_unrelated_google_paths():
    url = 'https://translate.google.com/about?u=x'
    assert unwrap_redirector(url) == url


def test_decode_feedsportal():
    # Segments are separated by '0'; the first is dropped and each following
    # segment starts with a code letter (M = https://, B = ., C = /).
    token = 'A0M0example0B0com0C0x'
    assert decode_feedsportal(
        'https://feedsportal.com/%s/story01.htm' % token) == 'https://example.com/x'


def test_decode_feedsportal_leaves_plain_urls_alone():
    url = 'https://example.com/story01.htm'
    assert decode_feedsportal(url) == url
