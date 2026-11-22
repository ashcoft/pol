"""Feed reading, discovery and full-text extraction for pol.

The package is deliberately independent from Twisted, Django and the database so it can
be used from the downloader server, the Django frontend and the command line.
"""

from .model import Feed, Item
from .pipeline import Options, ProcessResult, process
from .discover import FeedRef, discover_from_html, find_feeds
from .parse import parse_feed

__all__ = [
    'Feed',
    'Item',
    'FeedRef',
    'Options',
    'ProcessResult',
    'process',
    'parse_feed',
    'find_feeds',
    'discover_from_html',
]
