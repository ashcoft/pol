"""URL normalisation and tracking-link cleanup.

The normalisation rules mirror ashcoft/rss-finder: a bare host gets an https://
prefix, and only http(s) URLs are accepted.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, unquote, unquote_plus, urlsplit, urlunsplit

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
    'out.reddit.com': ('url',),
    'href.li': ('',),
    'anonym.to': ('',),
    'nullrefer.com': ('',),
}

_GOOGLE_HOST_RE = re.compile(r'^(?:www\.)?google\.[a-z.]+$', re.IGNORECASE)

# feedsportal hides the real URL in a /<token>/story01.htm path, one encoded
# character per pair. The map is morss's, so an existing feed keeps resolving.
_FEEDSPORTAL_RE = re.compile(r'/([0-9a-zA-Z]{20,})/story01\.htm$')
_FEEDSPORTAL_CODES = {
    'A': '0', 'B': '.', 'C': '/', 'D': '?', 'E': '-', 'F': '=', 'G': '&',
    'H': ',', 'I': '_', 'J': '%', 'K': '+', 'L': 'http://', 'M': 'https://',
    'N': '.com', 'O': '.co.uk', 'P': ';', 'Q': '|', 'R': ':', 'S': 'www.',
    'T': '#', 'U': '$', 'V': '~', 'W': '!', 'X': '(', 'Y': ')', 'Z': 'Z',
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
    """Remove campaign/analytics query parameters while keeping the rest.

    Retained parameters are copied as their original encoded segments so that
    signed URLs are not invalidated by a decode/re-encode round trip.
    """
    parts = urlsplit(url)
    if not parts.query:
        return url

    kept = []
    removed = False
    for segment in parts.query.split('&'):
        if not segment:
            continue
        name = unquote_plus(segment.split('=', 1)[0])
        if is_tracking_param(name):
            removed = True
            continue
        kept.append(segment)

    if not removed:
        return url
    return urlunsplit((parts.scheme, parts.netloc, parts.path,
                       '&'.join(kept), parts.fragment))


def _wrapper_keys(host, path):
    """Query keys holding the destination for this wrapper host, if it is one."""
    keys = _REDIRECT_WRAPPERS.get(host)
    if keys:
        return keys
    if _GOOGLE_HOST_RE.match(host) and path.startswith('/url'):
        # morss matches google.<any TLD>/url, not only google.com.
        return ('q', 'url')
    if host == 'news.google.com' and path.startswith('/news/url'):
        return ('url',)
    if host == 'getpocket.com' and path.startswith('/redirect'):
        return ('url',)
    if host.startswith('translate.google.') and path.startswith('/translate'):
        return ('u',)
    return None


def unwrap_redirector(url: str) -> str:
    """Return the destination hidden in a known redirect wrapper, if any."""
    parts = urlsplit(url)
    host = (parts.hostname or '').lower()
    keys = _wrapper_keys(host, parts.path)
    if not keys:
        return url

    if keys == ('',):
        # Path-only wrappers: https://href.li/?https://example.com
        target = parts.query
    else:
        values = dict(parse_qsl(parts.query, keep_blank_values=True))
        target = next((values[k] for k in keys if values.get(k)), '')

    target = unquote(target).strip()
    if not target or not _looks_like_target_url(target):
        return url
    try:
        return normalize_url(target)
    except InvalidURLError:
        return url


def decode_feedsportal(url: str) -> str:
    """Decode a feedsportal ``/<token>/story01.htm`` link into its real URL."""
    parts = urlsplit(url)
    match = _FEEDSPORTAL_RE.search(parts.path)
    if not match:
        return url
    decoded = ''.join(
        _FEEDSPORTAL_CODES.get(pair[0], pair[0]) + pair[1:]
        for pair in match.group(1).split('0')[1:]
    )
    if not _looks_like_target_url(decoded):
        return url
    try:
        return normalize_url(decoded)
    except InvalidURLError:
        return url


def _looks_like_target_url(value: str) -> bool:
    if value.lower().startswith(('http://', 'https://')):
        return True
    host = value.split('/', 1)[0]
    return '.' in host and ' ' not in host


def clean_url(url: str) -> str:
    """Unwrap redirectors, drop tracking parameters and fragments."""
    return defrag(strip_tracking(unwrap_redirector(url)))


def looks_like_feed_url(url: str) -> bool:
    parts = urlsplit(url)
    return bool(_FEED_HINT_RE.search(parts.path + ('?' + parts.query if parts.query else '')))
