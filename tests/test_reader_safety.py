import pytest

from pol.reader.errors import InvalidURLError
from pol.reader.http import Fetcher
from pol.reader.safety import assert_public_url, is_blocked_host
from pol.reader.web import ReaderEndpoints


@pytest.mark.parametrize('host', [
    'localhost', 'api.localhost', 'metadata.google.internal', 'router.local',
    '127.0.0.1', '10.1.2.3', '172.16.0.1', '192.168.1.1', '169.254.169.254',
    '100.64.0.1', '0.0.0.0', '224.0.0.1', '2130706433',
    '::1', 'fd00::1', 'fe80::1', '::ffff:127.0.0.1',
])
def test_blocks_private_and_local_hosts(host):
    assert is_blocked_host(host)


@pytest.mark.parametrize('host', [
    'example.com', 'feeds.bbci.co.uk', '8.8.8.8', '172.32.0.1', '2606:4700::1111',
])
def test_allows_public_hosts(host):
    assert not is_blocked_host(host)


def test_assert_public_url_accepts_a_public_url():
    url = 'https://example.com/feed.xml'
    assert assert_public_url(url) == url


@pytest.mark.parametrize('url', [
    'http://169.254.169.254/latest/meta-data/',
    'http://localhost:8080/feed.xml',
    'http://[::1]/feed.xml',
    'file:///etc/passwd',
])
def test_assert_public_url_rejects_private_targets(url):
    with pytest.raises(InvalidURLError):
        assert_public_url(url)


def test_guarded_fetcher_refuses_a_private_url_without_connecting(http_server):
    fetcher = Fetcher(timeout=2, block_private_hosts=True)
    with pytest.raises(InvalidURLError):
        fetcher.fetch(http_server.base_url + '/feed.xml')


def test_guarded_fetcher_refuses_a_redirect_to_a_private_host(http_server):
    http_server.routes['/hop'] = (
        302, {'Location': 'http://169.254.169.254/latest/meta-data/'}, '')
    fetcher = Fetcher(timeout=2, block_private_hosts=True)
    with pytest.raises(InvalidURLError):
        fetcher.fetch(http_server.base_url + '/hop')


def test_reader_endpoints_guard_private_hosts_by_default():
    endpoints = ReaderEndpoints('pol-test/1', cache_backend='memory')
    assert endpoints.block_private_hosts is True
