try:
    import requests
except ImportError:  # pragma: nocover
    requests = None

from pydantic import BaseModel, ValidationError

from lnurl.models.generics import HttpsUrl, Lnurl
from lnurl.models.responses import LnurlResponse, LnurlAuthResponse
from lnurl.tools import _url_encode
from .exceptions import InvalidLnurl, InvalidUrl


class _LnurlModel(BaseModel):
    lnurl: Lnurl


def decode(bech32_lnurl: str) -> HttpsUrl:
    try:
        return _LnurlModel(lnurl=bech32_lnurl).lnurl.url
    except ValidationError:
        raise InvalidLnurl


def encode(url: str) -> Lnurl:
    try:
        return _LnurlModel(lnurl=_url_encode(url)).lnurl
    except (ValidationError, ValueError):
        raise InvalidUrl


def handle(bech32_lnurl: str) -> LnurlResponse:
    try:
        lnurl = _LnurlModel(lnurl=bech32_lnurl).lnurl
    except ValidationError:
        raise InvalidLnurl

    if lnurl.is_login:
        return LnurlAuthResponse(**{
            'callback': lnurl.url,
            'k1': lnurl.url.query_params['k1']
        })
    else:
        if requests is None:  # pragma: nocover
            raise ImportError('The `requests` library must be installed to use `lnurl.handle()`.')

        r = requests.get(lnurl.url)
        return LnurlResponse.from_dict(r.json())
