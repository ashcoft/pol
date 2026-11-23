"""URL validation for the downloader's page and feed routes."""

import pytest

from pol.server import _http_url


@pytest.mark.parametrize('value', [
    b'https://example.com/article',
    'http://example.com/',
    ' https://example.com/path ',
])
def test_http_url_accepts_absolute_http_urls(value):
    assert _http_url(value).startswith(('http://', 'https://'))


@pytest.mark.parametrize('value', [
    b'',
    b'   ',
    b'example.com',
    b'//example.com',
    b'/relative/path',
    b'mailto:x@example.com',
    b'javascript:alert(1)',
    b'ftp://example.com',
    b'http://',
])
def test_http_url_rejects_unsupported_values(value):
    assert _http_url(value) is None
