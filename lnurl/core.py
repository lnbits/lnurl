from typing import Any, Optional, Union

import requests
from pydantic import ValidationError

from .exceptions import InvalidLnurl, InvalidUrl, LnurlResponseException
from .helpers import encode_strict_der, lnurlauth_key, url_encode
from .models import LnurlResponse, LnurlResponseModel
from .types import ClearnetUrl, DebugUrl, Lnurl, OnionUrl


def decode(bech32_lnurl: str) -> Union[OnionUrl, ClearnetUrl, DebugUrl]:
    try:
        return Lnurl(bech32_lnurl).url
    except (ValidationError, ValueError):
        raise InvalidLnurl


def encode(url: str) -> Lnurl:
    try:
        return Lnurl(url_encode(url))
    except (ValidationError, ValueError):
        raise InvalidUrl


def get(url: str, *, response_class: Optional[Any] = None, verify: Union[str, bool] = True) -> LnurlResponseModel:
    try:
        req = requests.get(url, verify=verify)
        req.raise_for_status()
    except Exception as e:
        raise LnurlResponseException(str(e))

    if response_class:
        assert issubclass(response_class, LnurlResponseModel), "Use a valid `LnurlResponseModel` subclass."
        return response_class(**req.json())

    return LnurlResponse.from_dict(req.json())


def handle(
    bech32_lnurl: str,
    response_class: Optional[LnurlResponseModel] = None,
    verify: Union[str, bool] = True,
    login_id: Optional[str] = None,
) -> LnurlResponseModel:
    try:
        if "@" in bech32_lnurl:
            lnaddress = LnAddress(bech32_lnurl)
            return get(lnaddress.url, response_class=response_class, verify=verify)
        lnurl = Lnurl(bech32_lnurl)
    except (ValidationError, ValueError):
        raise InvalidLnurl

    if lnurl.is_login:
        try:
            return auth(lnurl, login_id=login_id, verify=verify)
        except (ValidationError, ValueError):
            raise InvalidLnurl

    return get(lnurl.url, response_class=response_class, verify=verify)


def auth(
    lnurl: Lnurl,
    response_class: Optional[Any] = None,
    login_id: Optional[str] = None,
    verify: Union[str, bool] = True,
) -> LnurlResponseModel:
    k1 = bytes.fromhex(lnurl.url.query_params["k1"])
    assert login_id, "Provide a valid login_id to sign the message."
    auth_key = lnurlauth_key(lnurl.url.netloc, login_id)
    sig = auth_key.sign_digest_deterministic(k1, sigencode=encode_strict_der)
    assert auth_key.verifying_key, "LNURLauth verifying_key does not exist"
    try:
        req = requests.get(
            lnurl.url,
            verify=verify,
            params={
                "k1": k1.hex(),
                "key": auth_key.verifying_key.to_string("compressed").hex(),
                "sig": sig.hex(),
            },
        )
        req.raise_for_status()
    except Exception as e:
        raise LnurlResponseException(str(e))

    if response_class:
        assert issubclass(response_class, LnurlResponseModel), "Use a valid `LnurlResponseModel` subclass."
        return response_class(**req.json())

    return LnurlResponse.from_dict(req.json())
    # return LnurlErrorResponse(reason=withdraw.reason)
