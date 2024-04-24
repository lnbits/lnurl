import httpx
from typing import Any, Optional, Union

from bolt11 import Bolt11Exception, MilliSatoshi
from bolt11 import decode as bolt11_decode
from pydantic import ValidationError

from .exceptions import InvalidLnurl, InvalidUrl, LnurlResponseException
from .helpers import lnurlauth_signature, url_encode
from .models import LnurlAuthResponse, LnurlPayResponse, LnurlResponse, LnurlResponseModel, LnurlWithdrawResponse
from .types import ClearnetUrl, DebugUrl, LnAddress, Lnurl, OnionUrl


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


async def get(url: str, *, response_class: Optional[Any] = None) -> LnurlResponseModel:
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url)
            res.raise_for_status()
        except Exception as e:
            raise LnurlResponseException(str(e))

        if response_class:
            assert issubclass(response_class, LnurlResponseModel), "Use a valid `LnurlResponseModel` subclass."
            return response_class(**res.json())

        return LnurlResponse.from_dict(res.json())


async def handle(
    bech32_lnurl: str,
    response_class: Optional[LnurlResponseModel] = None,
) -> LnurlResponseModel:
    try:
        if "@" in bech32_lnurl:
            lnaddress = LnAddress(bech32_lnurl)
            return await get(lnaddress.url, response_class=response_class)
        lnurl = Lnurl(bech32_lnurl)
    except (ValidationError, ValueError):
        raise InvalidLnurl

    if lnurl.is_login:
        return LnurlAuthResponse(callback=lnurl.url, k1=lnurl.url.query_params["k1"])

    return await get(lnurl.url, response_class=response_class)


async def execute(bech32_or_address: str, value: str) -> LnurlResponseModel:
    try:
        res = handle(bech32_or_address)
    except Exception as exc:
        raise LnurlResponseException(str(exc))

    if isinstance(res, LnurlPayResponse) and res.tag == "payRequest":
        return await execute_pay_request(res, value)
    elif isinstance(res, LnurlAuthResponse) and res.tag == "login":
        return await execute_login(res, value)
    elif isinstance(res, LnurlWithdrawResponse) and res.tag == "withdrawRequest":
        return await execute_withdraw(res, value)

    raise LnurlResponseException(f"{res.tag} not implemented")  # type: ignore


async def execute_pay_request(res: LnurlPayResponse, msat: str) -> LnurlResponseModel:
    if not res.min_sendable <= MilliSatoshi(msat) <= res.max_sendable:
        raise LnurlResponseException(f"Amount {msat} not in range {res.min_sendable} - {res.max_sendable}")
    try:
        async with httpx.AsyncClient() as client:
            res2 = await client.get(
                url=res.callback,
                params={
                    "amount": msat,
                },
            )
            res2.raise_for_status()
            return LnurlResponse.from_dict(res2.json())
    except Exception as exc:
        raise LnurlResponseException(str(exc))


async def execute_login(res: LnurlAuthResponse, secret: str) -> LnurlResponseModel:
    try:
        assert res.callback.host, "LNURLauth host does not exist"
        key, sig = lnurlauth_signature(res.callback.host, secret, res.k1)
        async with httpx.AsyncClient() as client:
            res2 = await client.get(
                url=res.callback,
                params={
                    "key": key,
                    "sig": sig,
                },
            )
            res2.raise_for_status()
            return LnurlResponse.from_dict(res2.json())
    except Exception as e:
        raise LnurlResponseException(str(e))


async def execute_withdraw(res: LnurlWithdrawResponse, pr: str) -> LnurlResponseModel:
    try:
        invoice = bolt11_decode(pr)
    except Bolt11Exception as exc:
        raise LnurlResponseException(str(exc))
    # if invoice does not have amount use the min withdrawable amount
    amount = invoice.amount_msat or res.min_withdrawable
    if not res.min_withdrawable <= MilliSatoshi(amount) <= res.max_withdrawable:
        raise LnurlResponseException(f"Amount {amount} not in range {res.min_withdrawable} - {res.max_withdrawable}")
    try:
        async with httpx.AsyncClient() as client:
            res2 = await client.get(
                url=res.callback,
                params={
                    "k1": res.k1,
                    "pr": pr,
                },
            )
            res2.raise_for_status()
            return LnurlResponse.from_dict(res2.json())
    except Exception as exc:
        raise LnurlResponseException(str(exc))
