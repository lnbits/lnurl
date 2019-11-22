class LnurlException(Exception):
    """A LNURL error occurred."""


class InvalidLnurl(LnurlException, ValueError):
    """The LNURL provided was somehow invalid."""


class InvalidUrl(LnurlException, ValueError):
    """The URL is not properly formed."""


class InvalidScheme(InvalidUrl):
    """The URL scheme is not `https`."""


class LnurlResponseException(LnurlException):
    """An error ocurred processing LNURL response."""


class InvalidLnurlTag(LnurlResponseException, ValueError):
    """The response `tag` doesn't match the selected LnurlResponse subclass `_tag`."""


class InvalidLnurlPayMetadata(LnurlResponseException, ValueError):
    """The response `metadata` is not properly formed."""
