from json import JSONDecodeError
from typing import Any, Optional

import httpx
from bolt11 import Bolt11Exception, MilliSatoshi
from bolt11 import decode as bolt11_decode
from pydantic import ValidationError, parse_obj_as

from .exceptions import InvalidLnurl, InvalidUrl, LnurlResponseException
from .helpers import (
    lnurlauth_derive_linking_key,
    lnurlauth_derive_linking_key_sign_message,
    lnurlauth_signature,
    url_encode,
)
from .models import (
    LnurlAuthResponse,
    LnurlErrorResponse,
    LnurlPayActionResponse,
    LnurlPayResponse,
    LnurlResponse,
    LnurlResponseModel,
    LnurlSuccessResponse,
    LnurlWithdrawResponse,
)
from .types import CallbackUrl, LnAddress, Lnurl

USER_AGENT = "lnbits/lnurl"
TIMEOUT = 5


def decode(lnurl: str) -> Lnurl:
    try:
        return Lnurl(lnurl)
    except (ValidationError, ValueError):
        raise InvalidLnurl


def encode(url: str) -> Lnurl:
    try:
        return Lnurl(url_encode(url))
    except (ValidationError, ValueError):
        raise InvalidUrl


async def get(
    url: str,
    *,
    response_class: Optional[Any] = None,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
) -> LnurlResponseModel:
    headers = {"User-Agent": user_agent or USER_AGENT}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            res = await client.get(url, timeout=timeout or TIMEOUT)
            res.raise_for_status()
        except Exception as exc:
            raise LnurlResponseException(str(exc)) from exc

        try:
            _json = res.json()
        except JSONDecodeError as exc:
            raise LnurlResponseException(f"Invalid JSON response from {url}") from exc

        if response_class:
            if not issubclass(response_class, LnurlResponseModel):
                raise LnurlResponseException("response_class must be a subclass of LnurlResponseModel")
            return response_class(**_json)

        return LnurlResponse.from_dict(_json)


async def handle(
    lnurl: str,
    response_class: Optional[LnurlResponseModel] = None,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
) -> LnurlResponseModel:
    try:
        if "@" in lnurl:
            lnaddress = LnAddress(lnurl)
            return await get(lnaddress.url, response_class=response_class, user_agent=user_agent, timeout=timeout)
        lnurl = Lnurl(lnurl)
    except (ValidationError, ValueError):
        raise InvalidLnurl

    if lnurl.is_login:
        callback_url = parse_obj_as(CallbackUrl, lnurl.url)
        return LnurlAuthResponse(callback=callback_url, k1=lnurl.url.query_params["k1"])

    return await get(lnurl.url, response_class=response_class, user_agent=user_agent, timeout=timeout)


async def execute(
    bech32_or_address: str,
    value: str,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
) -> LnurlResponseModel:
    try:
        res = await handle(bech32_or_address, user_agent=user_agent, timeout=timeout)
    except Exception as exc:
        raise LnurlResponseException(str(exc))

    if isinstance(res, LnurlPayResponse) and res.tag == "payRequest":
        return await execute_pay_request(res, int(value), user_agent=user_agent, timeout=timeout)
    elif isinstance(res, LnurlAuthResponse) and res.tag == "login":
        return await execute_login(res, value, user_agent=user_agent, timeout=timeout)
    elif isinstance(res, LnurlWithdrawResponse) and res.tag == "withdrawRequest":
        return await execute_withdraw(res, value, user_agent=user_agent, timeout=timeout)

    raise LnurlResponseException("tag not implemented")


async def execute_pay_request(
    res: LnurlPayResponse,
    msat: int,
    comment: Optional[str] = None,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
) -> LnurlPayActionResponse:
    if not res.minSendable <= MilliSatoshi(msat) <= res.maxSendable:
        raise LnurlResponseException(f"Amount {msat} not in range {res.minSendable} - {res.maxSendable}")

    params: dict[str, str | int] = {"amount": msat}

    if res.commentAllowed and comment:
        if len(comment) > res.commentAllowed:
            raise LnurlResponseException(f"Comment length {len(comment)} exceeds allowed length {res.commentAllowed}")
        params["comment"] = comment

    try:
        headers = {"User-Agent": user_agent or USER_AGENT}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            res2 = await client.get(
                url=res.callback,
                params=params,
                timeout=timeout or TIMEOUT,
            )
            res2.raise_for_status()
            pay_res = LnurlResponse.from_dict(res2.json())
            if isinstance(pay_res, LnurlErrorResponse):
                raise LnurlResponseException(pay_res.reason)
            if not isinstance(pay_res, LnurlPayActionResponse):
                raise LnurlResponseException(f"Expected LnurlPayActionResponse, got {type(pay_res)}")
            invoice = bolt11_decode(pay_res.pr)
            if invoice.amount_msat != int(msat):
                raise LnurlResponseException(
                    f"{res.callback.host} returned an invalid invoice."
                    f"Excepted `{msat}` msat, got `{invoice.amount_msat}`."
                )
            return pay_res
    except Exception as exc:
        raise LnurlResponseException(str(exc))


async def execute_login(
    res: LnurlAuthResponse,
    seed: str | None = None,
    signed_message: str | None = None,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
) -> LnurlResponseModel:
    if not res.callback:
        raise LnurlResponseException("LNURLauth callback does not exist")
    host = res.callback.host
    if not host:
        raise LnurlResponseException("Invalid host in LNURLauth callback")
    if seed:
        linking_key, _ = lnurlauth_derive_linking_key(seed=seed, domain=host)
    elif signed_message:
        linking_key, _ = lnurlauth_derive_linking_key_sign_message(domain=host, sig=signed_message.encode())
    else:
        raise LnurlResponseException("Seed or signed_message is required for LNURLauth")
    try:
        key, sig = lnurlauth_signature(res.k1, linking_key=linking_key)
        headers = {"User-Agent": user_agent or USER_AGENT}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            res2 = await client.get(
                url=res.callback,
                params={
                    "key": key,
                    "sig": sig,
                },
                timeout=timeout or TIMEOUT,
            )
            res2.raise_for_status()
            return LnurlResponse.from_dict(res2.json())
    except Exception as e:
        raise LnurlResponseException(str(e))


async def execute_withdraw(
    res: LnurlWithdrawResponse,
    pr: str,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
) -> LnurlSuccessResponse:
    try:
        invoice = bolt11_decode(pr)
    except Bolt11Exception as exc:
        raise LnurlResponseException(str(exc))
    # if invoice does not have amount use the min withdrawable amount
    amount = invoice.amount_msat or res.minWithdrawable
    if not res.minWithdrawable <= MilliSatoshi(amount) <= res.maxWithdrawable:
        raise LnurlResponseException(f"Amount {amount} not in range {res.minWithdrawable} - {res.maxWithdrawable}")
    try:
        headers = {"User-Agent": user_agent or USER_AGENT}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            res2 = await client.get(
                url=res.callback,
                params={
                    "k1": res.k1,
                    "pr": pr,
                },
                timeout=timeout or TIMEOUT,
            )
            res2.raise_for_status()
            withdraw_res = LnurlResponse.from_dict(res2.json())
            if isinstance(withdraw_res, LnurlErrorResponse):
                raise LnurlResponseException(withdraw_res.reason)
            if not isinstance(withdraw_res, LnurlSuccessResponse):
                raise LnurlResponseException(f"Expected LnurlSuccessResponse, got {type(withdraw_res)}")
            return withdraw_res
    except Exception as exc:
        raise LnurlResponseException(str(exc))
