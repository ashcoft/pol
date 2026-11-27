import socket

import pytest

from pol.reader.errors import InvalidURLError, UnresolvableURLError
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


def test_hostname_resolving_to_a_private_address_is_rejected():
    with pytest.raises(InvalidURLError):
        assert_public_url('http://internal.example.com/feed.xml',
                          resolver=lambda host: ['10.0.0.5'])


def test_hostname_with_one_private_answer_is_rejected():
    with pytest.raises(InvalidURLError):
        assert_public_url('http://mixed.example.com/feed.xml',
                          resolver=lambda host: ['93.184.216.34', '127.0.0.1'])


def test_hostname_with_only_public_answers_is_allowed():
    url = 'http://public.example.com/feed.xml'
    assert assert_public_url(url, resolver=lambda host: ['93.184.216.34']) == url


def test_resolver_failure_is_not_reported_as_a_refused_host():
    def resolver(host):
        raise socket.gaierror(-3, 'Temporary failure in name resolution')

    with pytest.raises(UnresolvableURLError) as excinfo:
        assert_public_url('http://example.com/feed.xml', resolver=resolver)
    assert isinstance(excinfo.value, InvalidURLError)
    assert 'could not be resolved' in str(excinfo.value)


def test_redirect_handler_refuses_a_private_hop():
    from pol.reader.http import GuardedRedirectHandler

    class _Request:
        full_url = 'https://example.com/feed.xml'

    handler = GuardedRedirectHandler()
    with pytest.raises(InvalidURLError):
        handler.redirect_request(_Request(), None, 302, 'Found', {},
                                 'http://169.254.169.254/latest/meta-data/')


def test_guarded_fetcher_refuses_to_resolve_private_links(http_server):
    fetcher = Fetcher(timeout=2, block_private_hosts=True)
    with pytest.raises(InvalidURLError):
        fetcher.resolve('http://169.254.169.254/latest/meta-data/')
