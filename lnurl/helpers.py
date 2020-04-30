from bech32 import bech32_decode, bech32_encode, convertbits
from typing import List, Set, Tuple

from .exceptions import InvalidLnurl, InvalidUrl


def _bech32_decode(bech32: str, *, allowed_hrp: Set[str] = None) -> Tuple[str, List[int]]:
    hrp, data = bech32_decode(bech32)

    if not hrp or not data or (allowed_hrp and hrp not in allowed_hrp):
        raise ValueError(f"Invalid data or Human Readable Prefix (HRP): {hrp}.")

    return hrp, data


def _lnurl_clean(lnurl: str) -> str:
    lnurl = lnurl.strip()
    return lnurl.replace("lightning:", "") if lnurl.startswith("lightning:") else lnurl


def _lnurl_decode(lnurl: str) -> str:
    """
    Decode a LNURL and return a url string without performing any validation on it.
    Use `lnurl.decode()` for validation and to get `Url` object.
    """
    hrp, data = _bech32_decode(_lnurl_clean(lnurl), allowed_hrp={"lnurl"})

    try:
        bech32_data = convertbits(data, 5, 8, False)
        assert bech32_data
        url = bytes(bech32_data).decode("utf-8")
    except UnicodeDecodeError:  # pragma: nocover
        raise InvalidLnurl

    return url


def _url_encode(url: str) -> str:
    """
    Encode a URL without validating it first and return a bech32 LNURL string.
    Use `lnurl.encode()` for validation and to get a `Lnurl` object.
    """
    try:
        bech32_data = convertbits(url.encode("utf-8"), 8, 5, True)
        assert bech32_data
        lnurl = bech32_encode("lnurl", bech32_data)
    except UnicodeEncodeError:  # pragma: nocover
        raise InvalidUrl

    return lnurl.upper()
