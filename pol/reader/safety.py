"""Reject fetches aimed at private or reserved network destinations.

Mirrors the guard added to ashcoft/rss-finder, plus a resolver check: Python can
see the addresses a hostname resolves to, so a name pointing at a private
address is refused too. The HTTP layer re-checks every redirect hop.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from .errors import InvalidURLError

BLOCKED_HOSTNAMES = frozenset({'localhost', 'metadata', 'metadata.google.internal'})
BLOCKED_SUFFIXES = ('.localhost', '.local', '.internal', '.home.arpa')


def is_blocked_host(hostname: str) -> bool:
    """True for local names, integer IPv4 forms and any non-global IP address."""
    host = (hostname or '').strip().lower().rstrip('.')
    if host.startswith('[') and host.endswith(']'):
        host = host[1:-1]
    if not host:
        return True
    if host in BLOCKED_HOSTNAMES:
        return True
    if host.endswith(BLOCKED_SUFFIXES):
        return True
    # Integer form, e.g. http://2130706433/ for 127.0.0.1.
    if host.isdigit():
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return not address.is_global or address.is_multicast or address.is_reserved


def resolve_addresses(hostname: str):
    """Every address a hostname resolves to, as strings."""
    infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    return sorted({info[4][0] for info in infos})


def assert_public_url(url: str, resolver=resolve_addresses) -> str:
    """Return ``url`` unchanged, or raise InvalidURLError when it targets a private host.

    The hostname is resolved and every address it points at is checked, so a public name
    that resolves to a private address is refused as well. The connection itself is still
    made by the transport, so a name that changes its answer between the check and the
    connect (DNS rebinding) is not covered.
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in ('http', 'https'):
        raise InvalidURLError('URL must use http or https')

    host = parts.hostname or ''
    if is_blocked_host(host):
        raise InvalidURLError('URL host is not allowed')
    try:
        parts.port  # noqa: B018 - validates the port
    except ValueError as exc:
        raise InvalidURLError('Invalid URL port') from exc

    if resolver is None:
        return url

    try:
        addresses = resolver(host)
    except (socket.gaierror, OSError) as exc:
        raise InvalidURLError('URL host could not be resolved') from exc

    if any(is_blocked_host(address) for address in addresses):
        raise InvalidURLError('URL host is not allowed')
    return url
