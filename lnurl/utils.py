import re

from bech32 import bech32_decode, bech32_encode, convertbits
from urllib.parse import urlparse

from .exceptions import InvalidLnurl, InvalidScheme, InvalidUrl


URL_MAXLENGTH = 4096  # arbitrary
CTRL = re.compile(r'[\u0000-\u001f\u007f-\u009f]')  # control characters (unicode blocks C0 and C1, plus DEL)
NON_RFC3986 = re.compile(r"[^]a-zA-Z0-9._~:/?#[@!$&'()*+,;=-]")


def decode(lnurl: str, *, strict_rfc3986: bool = False, allow_long: bool = False) -> str:
    lnurl = lnurl.replace('lightning:', '') if lnurl.startswith('lightning:') else lnurl
    hrp, data = bech32_decode(lnurl)

    if None in (hrp, data) or hrp != 'lnurl':
        raise InvalidLnurl

    try:
        url = bytes(convertbits(data, 5, 8, False)).decode('utf-8')
    except UnicodeDecodeError:  # pragma: nocover
        raise InvalidLnurl

    validate_url(url, strict_rfc3986=strict_rfc3986, allow_long=allow_long)

    return url


def encode(url: str) -> str:
    validate_url(url, strict_rfc3986=True, allow_long=False)

    try:
        lnurl = bech32_encode('lnurl', convertbits(url.encode('utf-8'), 8, 5, True))
    except UnicodeEncodeError:  # pragma: nocover
        raise InvalidUrl

    return lnurl.upper()


def validate_url(url: str, *, strict_rfc3986: bool = False, allow_long: bool = False) -> None:
    if not allow_long and len(url) > URL_MAXLENGTH:
        raise InvalidUrl('too long HTTPS URL')

    if (strict_rfc3986 and NON_RFC3986.search(url)) or CTRL.search(url):
        raise InvalidUrl('invalid characters in HTTPS URL')

    try:
        parsed = urlparse(url)
    except ValueError:  # pragma: nocover
        raise InvalidUrl

    if not parsed.netloc or not parsed.hostname:
        raise InvalidUrl

    if parsed.scheme != 'https':
        raise InvalidScheme


def snake_keys(d: dict) -> dict:
    return {re.sub('([A-Z]+)', r'_\1', k).lower(): v for k, v in d.items()}
