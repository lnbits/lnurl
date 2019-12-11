class LnurlException(Exception):
    """A LNURL error occurred."""


class LnurlResponseException(LnurlException):
    """An error ocurred processing LNURL response."""


class InvalidLnurl(LnurlException, ValueError):
    """The LNURL provided was somehow invalid."""


class InvalidUrl(LnurlException, ValueError):
    """The URL is not properly formed."""


class InvalidLnurlPayMetadata(LnurlResponseException, ValueError):
    """The response `metadata` is not properly formed."""
