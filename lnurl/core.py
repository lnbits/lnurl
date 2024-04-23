from typing import Any, Optional, Union

import requests
from pydantic import ValidationError

from .exceptions import InvalidLnurl, InvalidUrl, LnurlResponseException
from .helpers import encode_strict_der, lnurlauth_key, url_encode
from .models import LnurlAuthResponse, LnurlPayResponse, LnurlResponse, LnurlResponseModel
from .types import ClearnetUrl, DebugUrl, LnAddress, Lnurl, MilliSatoshi, OnionUrl


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
) -> LnurlResponseModel:
    try:
        if "@" in bech32_lnurl:
            lnaddress = LnAddress(bech32_lnurl)
            return get(lnaddress.url, response_class=response_class, verify=verify)
        lnurl = Lnurl(bech32_lnurl)
    except (ValidationError, ValueError):
        raise InvalidLnurl

    if lnurl.is_login:
        return LnurlAuthResponse(callback=lnurl.url, k1=lnurl.url.query_params["k1"])

    return get(lnurl.url, response_class=response_class, verify=verify)


def execute(bech32_or_address: str, value: str) -> LnurlResponseModel:
    try:
        res = handle(bech32_or_address)
    except Exception as exc:
        raise LnurlResponseException(str(exc))

    if isinstance(res, LnurlPayResponse) and res.tag == "payRequest":
        return execute_pay_request(res, value)
    elif isinstance(res, LnurlAuthResponse) and res.tag == "login":
        return execute_login(res, value)

    raise Exception(f"{res.tag} not implemented")  # type: ignore


def execute_pay_request(res: LnurlPayResponse, msat: str) -> LnurlResponseModel:
    if res.max_sendable < MilliSatoshi(msat) < res.min_sendable:
        raise LnurlResponseException(f"Amount {msat} not in range {res.min_sendable} - {res.max_sendable}")
    try:
        req = requests.get(
            res.callback,
            params={
                "amount": msat,
            },
        )
        req.raise_for_status()
        return LnurlResponse.from_dict(req.json())
    except Exception as exc:
        raise LnurlResponseException(str(exc))


def execute_login(res: LnurlAuthResponse, value: str) -> LnurlResponseModel:
    try:
        k1 = bytes.fromhex(res.k1)
        assert res.callback.host, "LNURLauth host does not exist"
        auth_key = lnurlauth_key(res.callback.host, value)
        sig = auth_key.sign_digest_deterministic(k1, sigencode=encode_strict_der)
        assert auth_key.verifying_key, "LNURLauth verifying_key does not exist"
        req = requests.get(
            res.callback,
            params={
                "key": auth_key.verifying_key.to_string("compressed").hex(),
                "sig": sig.hex(),
            },
        )
        req.raise_for_status()
        return LnurlResponse.from_dict(req.json())
    except Exception as e:
        raise LnurlResponseException(str(e))
