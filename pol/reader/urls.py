"""URL normalisation and tracking-link cleanup.

The normalisation rules mirror ashcoft/rss-finder: a bare host gets an https://
prefix, and only http(s) URLs are accepted.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from .errors import InvalidURLError

# `scheme:` not followed by a digit, so `example.com:8080` is host:port.
_SCHEME_RE = re.compile(r'^([a-z][a-z0-9+.-]*):(?!\d)', re.IGNORECASE)
_FEED_HINT_RE = re.compile(
    r'(?:^|/)(?:feeds?|rss|atom)(?:/|$)|\.(?:rss|atom|xml|json)(?:$|[?#])',
    re.IGNORECASE,
)

TRACKING_PARAMS = frozenset({
    'fbclid', 'gclid', 'dclid', 'gbraid', 'wbraid', 'msclkid', 'yclid',
    'igshid', 'igsh', 'mc_cid', 'mc_eid', 'mkt_tok', 'oly_anon_id',
    'oly_enc_id', 'vero_id', 'vero_conv', '_hsenc', '_hsmi', 'hsctatracking',
})
TRACKING_PREFIXES = ('utm_', 'pk_', 'piwik_', 'matomo_')

# Wrapper hosts that only exist to redirect. The payload is in a query value.
_REDIRECT_WRAPPERS = {
    'l.facebook.com': ('u',),
    'lm.facebook.com': ('u',),
    'm.facebook.com': ('u',),
    'l.instagram.com': ('u',),
    'away.vk.com': ('to',),
    'www.google.com': ('q', 'url'),
    'google.com': ('q', 'url'),
    'out.reddit.com': ('url',),
    'href.li': ('',),
    'anonym.to': ('',),
    'nullrefer.com': ('',),
}


def normalize_url(url: str) -> str:
    """Return an absolute http(s) URL, adding https:// to bare hosts."""
    if not url or not str(url).strip():
        raise InvalidURLError('URL is required')

    trimmed = str(url).strip()
    scheme = _SCHEME_RE.match(trimmed)
    candidate = trimmed if scheme else 'https://' + trimmed

    try:
        parts = urlsplit(candidate)
        host = parts.hostname
        parts.port  # noqa: B018 - raises ValueError for invalid ports
    except ValueError as exc:
        raise InvalidURLError('Invalid URL format') from exc

    if parts.scheme.lower() not in ('http', 'https') or not host:
        raise InvalidURLError('Invalid URL format')

    return candidate


def is_http_url(url: str) -> bool:
    try:
        normalize_url(url)
    except InvalidURLError:
        return False
    return True


def defrag(url: str) -> str:
    """Drop the fragment, which is never sent to the server."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))


def is_tracking_param(name: str) -> bool:
    lowered = name.lower()
    return lowered in TRACKING_PARAMS or lowered.startswith(TRACKING_PREFIXES)


def strip_tracking(url: str) -> str:
    """Remove campaign/analytics query parameters while keeping the rest."""
    parts = urlsplit(url)
    if not parts.query:
        return url
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not is_tracking_param(k)]
    query = urlencode(kept, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def unwrap_redirector(url: str) -> str:
    """Return the destination hidden in a known redirect wrapper, if any."""
    parts = urlsplit(url)
    host = (parts.hostname or '').lower()
    keys = _REDIRECT_WRAPPERS.get(host)
    if not keys:
        return url

    if keys == ('',):
        # Path-only wrappers: https://href.li/?https://example.com
        target = parts.query
    else:
        values = dict(parse_qsl(parts.query, keep_blank_values=True))
        target = next((values[k] for k in keys if values.get(k)), '')

    target = unquote(target).strip()
    if not target:
        return url
    try:
        return normalize_url(target)
    except InvalidURLError:
        return url


def clean_url(url: str) -> str:
    """Unwrap redirectors, drop tracking parameters and fragments."""
    return defrag(strip_tracking(unwrap_redirector(url)))


def looks_like_feed_url(url: str) -> bool:
    parts = urlsplit(url)
    return bool(_FEED_HINT_RE.search(parts.path + ('?' + parts.query if parts.query else '')))
