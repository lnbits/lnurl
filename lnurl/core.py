try:
    import requests
except ImportError:  # pragma: nocover
    requests = None  # type: ignore

from pydantic import ValidationError
from typing import Any, Optional, Union

from .exceptions import LnurlResponseException, InvalidLnurl, InvalidUrl
from .helpers import _url_encode
from .models import LnurlResponse, LnurlResponseModel, LnurlAuthResponse
from .types import Lnurl, ClearnetUrl, OnionUrl


def decode(bech32_lnurl: str) -> Union[OnionUrl, ClearnetUrl]:
    try:
        return Lnurl(bech32_lnurl).url
    except (ValidationError, ValueError):
        raise InvalidLnurl


def encode(url: str) -> Lnurl:
    try:
        return Lnurl(_url_encode(url))
    except (ValidationError, ValueError):
        raise InvalidUrl


def get(url: str, *, response_class: Optional[Any] = None) -> LnurlResponseModel:
    if requests is None:  # pragma: nocover
        raise ImportError("The `requests` library must be installed to use `lnurl.get()` and `lnurl.handle()`.")

    try:
        r = requests.get(url)
    except Exception as e:
        raise LnurlResponseException(str(e))

    if response_class:
        assert issubclass(response_class, LnurlResponseModel), "Use a valid `LnurlResponseModel` subclass."
        return response_class(**r.json())

    return LnurlResponse.from_dict(r.json())


def handle(bech32_lnurl: str, *, response_class: Optional[LnurlResponseModel] = None) -> LnurlResponseModel:
    try:
        lnurl = Lnurl(bech32_lnurl)
    except (ValidationError, ValueError):
        raise InvalidLnurl

    if lnurl.is_login:
        return LnurlAuthResponse(callback=lnurl.url, k1=lnurl.url.query_params["k1"])

    return get(lnurl.url, response_class=response_class)
