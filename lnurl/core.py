from typing import Any, Optional, Union

import requests
from pydantic import ValidationError

from .exceptions import InvalidLnurl, InvalidUrl, LnurlResponseException
from .helpers import _url_encode
from .models import LnurlAuthResponse, LnurlResponse, LnurlResponseModel
from .types import ClearnetUrl, DebugUrl, Lnurl, OnionUrl


def decode(bech32_lnurl: str) -> Union[OnionUrl, ClearnetUrl, DebugUrl]:
    try:
        return Lnurl(bech32_lnurl).url
    except (ValidationError, ValueError):
        raise InvalidLnurl


def encode(url: str) -> Lnurl:
    try:
        return Lnurl(_url_encode(url))
    except (ValidationError, ValueError):
        raise InvalidUrl


def get(url: str, *, response_class: Optional[Any] = None, verify: Union[str, bool] = True) -> LnurlResponseModel:
    try:
        r = requests.get(url, verify=verify)
        r.raise_for_status()
    except Exception as e:
        raise LnurlResponseException(str(e))

    if response_class:
        assert issubclass(response_class, LnurlResponseModel), "Use a valid `LnurlResponseModel` subclass."
        return response_class(**r.json())

    return LnurlResponse.from_dict(r.json())


def handle(
    bech32_lnurl: str, *, response_class: Optional[LnurlResponseModel] = None, verify: Union[str, bool] = True
) -> LnurlResponseModel:
    try:
        lnurl = Lnurl(bech32_lnurl)
    except (ValidationError, ValueError):
        raise InvalidLnurl

    if lnurl.is_login:
        return LnurlAuthResponse(callback=lnurl.url, k1=lnurl.url.query_params["k1"])

    return get(lnurl.url, response_class=response_class)
