try:
    import requests
except ImportError:  # pragma: nocover
    requests = None

from pydantic import ValidationError

from .exceptions import InvalidLnurl, InvalidUrl
from .models import LnurlResponse, LnurlAuthResponse
from .functions import _url_encode
from .types import HttpsUrl, Lnurl


def decode(bech32_lnurl: str) -> HttpsUrl:
    try:
        return Lnurl(bech32_lnurl).url
    except (ValidationError, ValueError):
        raise InvalidLnurl


def encode(url: str) -> Lnurl:
    try:
        return Lnurl(_url_encode(url))
    except (ValidationError, ValueError):
        raise InvalidUrl


def get(url: str) -> LnurlResponse:
    if requests is None:  # pragma: nocover
        raise ImportError('The `requests` library must be installed to use `lnurl.handle()`.')

    r = requests.get(url)
    return LnurlResponse.from_dict(r.json())


def handle(bech32_lnurl: str) -> LnurlResponse:
    try:
        lnurl = Lnurl(bech32_lnurl)
    except (ValidationError, ValueError):
        raise InvalidLnurl

    if lnurl.is_login:
        return LnurlAuthResponse(**{
            'callback': lnurl.url,
            'k1': lnurl.url.query_params['k1']
        })

    return get(lnurl.url)
