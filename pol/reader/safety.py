"""Reject fetches aimed at private or reserved network destinations.

Mirrors the guard added to ashcoft/rss-finder: literal private addresses and local
hostnames are refused before a request is made, and again for the URL a redirect ends on.
Hostnames that *resolve* to a private address still need a resolver-level check.
"""

from __future__ import annotations

import ipaddress
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


def assert_public_url(url: str) -> str:
    """Return ``url`` unchanged, or raise InvalidURLError when it targets a private host."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in ('http', 'https'):
        raise InvalidURLError('URL must use http or https')
    if is_blocked_host(parts.hostname or ''):
        raise InvalidURLError('URL host is not allowed')
    return url
