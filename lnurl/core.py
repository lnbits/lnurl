from typing import Any, Optional

import httpx
from bolt11 import Bolt11Exception, MilliSatoshi
from bolt11 import decode as bolt11_decode
from pydantic import ValidationError

from .exceptions import InvalidLnurl, InvalidUrl, LnurlResponseException
from .helpers import (
    lnurlauth_derive_linking_key,
    lnurlauth_derive_linking_key_sign_message,
    lnurlauth_signature,
    url_encode,
)
from .models import (
    LnurlAuthResponse,
    LnurlPayActionResponse,
    LnurlPayResponse,
    LnurlResponse,
    LnurlResponseModel,
    LnurlWithdrawResponse,
)
from .types import LnAddress, Lnurl

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

        if response_class:
            assert issubclass(response_class, LnurlResponseModel), "Use a valid `LnurlResponseModel` subclass."
            return response_class(**res.json())

        return LnurlResponse.from_dict(res.json())


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
        return LnurlAuthResponse(callback=lnurl.callback_url, k1=lnurl.url.query_params["k1"])

    return await get(lnurl.callback_url, response_class=response_class, user_agent=user_agent, timeout=timeout)


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
        return await execute_pay_request(res, value, user_agent=user_agent, timeout=timeout)
    elif isinstance(res, LnurlAuthResponse) and res.tag == "login":
        return await execute_login(res, value, user_agent=user_agent, timeout=timeout)
    elif isinstance(res, LnurlWithdrawResponse) and res.tag == "withdrawRequest":
        return await execute_withdraw(res, value, user_agent=user_agent, timeout=timeout)

    raise LnurlResponseException(f"{res.tag} not implemented")  # type: ignore


async def execute_pay_request(
    res: LnurlPayResponse,
    msat: str,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
) -> LnurlResponseModel:
    if not res.min_sendable <= MilliSatoshi(msat) <= res.max_sendable:
        raise LnurlResponseException(f"Amount {msat} not in range {res.min_sendable} - {res.max_sendable}")

    try:
        headers = {"User-Agent": user_agent or USER_AGENT}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            res2 = await client.get(
                url=res.callback,
                params={
                    "amount": msat,
                },
                timeout=timeout or TIMEOUT,
            )
            res2.raise_for_status()
            pay_res = LnurlResponse.from_dict(res2.json())
            assert isinstance(pay_res, LnurlPayActionResponse), "Invalid response in execute_pay_request."
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
) -> LnurlResponseModel:
    try:
        invoice = bolt11_decode(pr)
    except Bolt11Exception as exc:
        raise LnurlResponseException(str(exc))
    # if invoice does not have amount use the min withdrawable amount
    amount = invoice.amount_msat or res.min_withdrawable
    if not res.min_withdrawable <= MilliSatoshi(amount) <= res.max_withdrawable:
        raise LnurlResponseException(f"Amount {amount} not in range {res.min_withdrawable} - {res.max_withdrawable}")
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
            return LnurlResponse.from_dict(res2.json())
    except Exception as exc:
        raise LnurlResponseException(str(exc))
