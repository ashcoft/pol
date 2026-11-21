class ReaderError(Exception):
    """Base class for all reader failures."""


class InvalidURLError(ReaderError, ValueError):
    """The supplied value is not a usable http(s) URL."""


class FetchError(ReaderError):
    """The remote document could not be retrieved."""

    def __init__(self, message, url=None, status=None):
        super().__init__(message)
        self.url = url
        self.status = status


class ParseError(ReaderError):
    """The document could not be interpreted as a feed or article."""


class DiscoveryError(ReaderError):
    """No feed could be found for a page."""
