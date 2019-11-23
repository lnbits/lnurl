import re

from bech32 import bech32_decode, bech32_encode, convertbits
from urllib.parse import urlparse

from .exceptions import InvalidLnurl, InvalidScheme, InvalidUrl


def validate_url(url: str, force_https: bool = True) -> None:
    try:
        parsed = urlparse(url)
    except ValueError:  # pragma: nocover
        raise InvalidUrl

    if force_https and parsed.scheme != 'https':
        raise InvalidScheme


def decode(lnurl: str, *, force_https: bool = True) -> str:
    lnurl = lnurl.replace('lightning:', '') if lnurl.startswith('lightning:') else lnurl
    hrp, data = bech32_decode(lnurl)

    if None in (hrp, data) or hrp != 'lnurl':
        raise InvalidLnurl

    try:
        url = bytes(convertbits(data, 5, 8, False)).decode('utf-8')
    except UnicodeDecodeError:  # pragma: nocover
        raise InvalidLnurl

    validate_url(url, force_https)
    return url


def encode(url: str, *, force_https: bool = True) -> str:
    validate_url(url, force_https)

    try:
        lnurl = bech32_encode('lnurl', convertbits(url.encode('utf-8'), 8, 5, True))
    except UnicodeEncodeError:  # pragma: nocover
        raise InvalidUrl

    return lnurl.upper()


def snake_keys(d: dict) -> dict:
    return {re.sub('([A-Z]+)', r'_\1', k).lower(): v for k, v in d.items()}
