import pytest

from pol.reader.errors import InvalidURLError
from pol.reader.urls import (
    clean_url,
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
