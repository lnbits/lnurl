try:
    import requests
except ImportError:  # pragma: nocover
    requests = None

from pydantic import ValidationError

from .exceptions import InvalidLnurl, InvalidUrl
from .helpers import _url_encode
from .models import LnurlResponse, LnurlResponseModel, LnurlAuthResponse
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


def get(url: str, *, response_class: LnurlResponseModel = None) -> LnurlResponseModel:
    if requests is None:  # pragma: nocover
        raise ImportError("The `requests` library must be installed to use `lnurl.get()` and `lnurl.handle()`.")

    r = requests.get(url)

    if response_class:
        return response_class(**r.json())

    return LnurlResponse.from_dict(r.json())


def handle(bech32_lnurl: str, *, response_class: LnurlResponseModel = None) -> LnurlResponseModel:
    try:
        lnurl = Lnurl(bech32_lnurl)
    except (ValidationError, ValueError):
        raise InvalidLnurl

    if lnurl.is_login:
        return LnurlAuthResponse(**{"callback": lnurl.url, "k1": lnurl.url.query_params["k1"]})

    return get(lnurl.url, response_class=response_class)
