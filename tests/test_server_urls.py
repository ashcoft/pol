"""URL validation for the downloader's page and feed routes."""

import socket

import pytest

from pol.server import Site, _http_url


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


def test_site_blocks_private_urls_unless_allowed():
    site = object.__new__(Site)
    site.allow_private = False
    assert site._url_allowed('http://127.0.0.1/') is False
    assert site._url_allowed('http://localhost/') is False

    site.allow_private = True
    assert site._url_allowed('http://127.0.0.1/') is True


def test_site_reports_a_host_that_cannot_be_resolved(monkeypatch):
    def no_dns(*args, **kwargs):
        raise socket.gaierror(-3, 'Temporary failure in name resolution')

    monkeypatch.setattr(socket, 'getaddrinfo', no_dns)

    site = object.__new__(Site)
    site.allow_private = False
    assert site._url_error('http://example.com/') == 'This URL could not be resolved.'
    assert site._url_allowed('http://example.com/') is False
