"""URL normalization shared by the discovery and setup views."""

import re
import urllib.parse

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

_SCHEME_RE = re.compile(r'^([a-z][a-z0-9+.-]*):(?!\d)', re.IGNORECASE)


def normalize_discovery_url(url):
    """Return an absolute http(s) URL with a lowercase scheme and host.

    A missing scheme defaults to https. The path, query and fragment keep
    their original case.
    """
    trimmed = (url or '').strip()
    if not trimmed:
        raise ValueError('URL is required')

    scheme = _SCHEME_RE.match(trimmed)
    candidate = trimmed if scheme else 'https://' + trimmed
    try:
        URLValidator(schemes=['http', 'https'])(candidate)
    except ValidationError as exc:
        raise ValueError('Invalid URL format') from exc

    parts = urllib.parse.urlsplit(candidate)
    userinfo, sep, hostport = parts.netloc.rpartition('@')
    netloc = (userinfo + sep if sep else '') + hostport.lower()
    return urllib.parse.urlunsplit((
        parts.scheme.lower(), netloc, parts.path, parts.query, parts.fragment))
