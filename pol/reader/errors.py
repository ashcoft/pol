class ReaderError(Exception):
    """Base class for all reader failures."""


class InvalidURLError(ReaderError, ValueError):
    """The supplied value is not a usable http(s) URL."""


class UnresolvableURLError(InvalidURLError):
    """The host name could not be looked up, so it can be neither checked nor fetched.

    A resolver failure says nothing about the URL itself, so callers that show
    the reason to a user should not report it as a refused address.
    """


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
