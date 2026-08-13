from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from json import JSONDecodeError
from typing import Any, Optional

import httpx
from bolt11 import Bolt11Exception, MilliSatoshi
from bolt11 import decode as bolt11_decode
from pydantic import TypeAdapter, ValidationError

from .exceptions import InvalidLnurl, InvalidUrl, LnAddressError, LnurlResponseException
from .helpers import (
    lnurlauth_derive_linking_key,
    lnurlauth_derive_linking_key_sign_message,
    lnurlauth_signature,
    url_encode,
)
from .models import (
    LnurlAddressRequestResponse,
    LnurlAuthResponse,
    LnurlErrorResponse,
    LnurlPayActionResponse,
    LnurlPayResponse,
    LnurlResponse,
    LnurlResponseModel,
    LnurlSuccessResponse,
    LnurlWithdrawResponse,
)
from .types import CallbackUrl, LnAddress, Lnurl, Url

TOR_SOCKS = "socks5h://127.0.0.1:9050"
USER_AGENT = "lnbits/lnurl"
TIMEOUT = 5


@asynccontextmanager
async def _http_client(
    client: Optional[httpx.AsyncClient],
    *,
    user_agent: Optional[str],
    proxy: Optional[str],
    timeout: Optional[int],
) -> AsyncIterator[httpx.AsyncClient]:
    if client is not None:
        yield client
        return

    headers = {"User-Agent": user_agent or USER_AGENT}
    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        proxy=proxy,
        timeout=timeout or TIMEOUT,
    ) as default_client:
        yield default_client


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
    url: str | Url | CallbackUrl,
    *,
    response_class: Optional[Any] = None,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
    tor_socks: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> LnurlResponseModel:
    request_url = str(url)
    proxy = tor_socks or TOR_SOCKS if ".onion" in request_url else None
    async with _http_client(client, user_agent=user_agent, proxy=proxy, timeout=timeout) as http_client:
        try:
            res = await http_client.get(request_url)
            res.raise_for_status()
        except httpx.ConnectError as exc:
            if proxy:
                raise LnurlResponseException(
                    f"Failed to connect to {request_url} via Tor proxy {proxy}. Is Tor running?"
                ) from exc
            raise LnurlResponseException(f"Failed to connect to {request_url}") from exc
        except Exception as exc:
            raise LnurlResponseException(str(exc)) from exc

        try:
            _json = res.json()
        except JSONDecodeError as exc:
            raise LnurlResponseException(f"Invalid JSON response from {request_url}") from exc

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
    tor_socks: Optional[str] = None,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> LnurlResponseModel:
    try:
        if "@" in lnurl:
            lnaddress = LnAddress(lnurl)
            return await get(
                lnaddress.url,
                response_class=response_class,
                user_agent=user_agent,
                timeout=timeout,
                client=client,
            )
        lnurl = Lnurl(lnurl)
    except (ValidationError, ValueError):
        raise InvalidLnurl

    if lnurl.is_login:
        callback_url = TypeAdapter(CallbackUrl).validate_python(lnurl.url)
        k1 = None
        for param in lnurl.url.query_params():
            if param[0] == "k1":
                k1 = param[1]
                break
        if not k1:
            raise LnurlResponseException("k1 parameter not found in LNURLauth URL")
        return LnurlAuthResponse(callback=callback_url, k1=k1)

    return await get(
        lnurl.url,
        response_class=response_class,
        user_agent=user_agent,
        timeout=timeout,
        tor_socks=tor_socks,
        client=client,
    )


async def execute(
    bech32_or_address: str,
    value: str,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
    tor_socks: Optional[str] = None,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> LnurlResponseModel:
    try:
        res = await handle(
            bech32_or_address,
            user_agent=user_agent,
            timeout=timeout,
            tor_socks=tor_socks,
            client=client,
        )
    except Exception as exc:
        raise LnurlResponseException(str(exc))

    if isinstance(res, LnurlPayResponse) and res.tag == "payRequest":
        return await execute_pay_request(
            res,
            int(value),
            user_agent=user_agent,
            timeout=timeout,
            tor_socks=tor_socks,
            client=client,
        )
    elif isinstance(res, LnurlAuthResponse) and res.tag == "login":
        return await execute_login(
            res,
            value,
            user_agent=user_agent,
            timeout=timeout,
            tor_socks=tor_socks,
            client=client,
        )
    elif isinstance(res, LnurlWithdrawResponse) and res.tag == "withdrawRequest":
        return await execute_withdraw(
            res,
            value,
            user_agent=user_agent,
            timeout=timeout,
            tor_socks=tor_socks,
            client=client,
        )
    elif isinstance(res, LnurlAddressRequestResponse) and res.tag == "addressRequest":
        return await execute_address_request(
            res,
            value,
            user_agent=user_agent,
            timeout=timeout,
            tor_socks=tor_socks,
            client=client,
        )

    raise LnurlResponseException("tag not implemented")


async def execute_pay_request(
    res: LnurlPayResponse,
    msat: int,
    comment: Optional[str] = None,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
    tor_socks: Optional[str] = None,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> LnurlPayActionResponse:
    if not res.minSendable <= MilliSatoshi(msat) <= res.maxSendable:
        raise LnurlResponseException(f"Amount {msat} not in range {res.minSendable} - {res.maxSendable}")

    params: dict[str, str | int] = {"amount": msat}

    if res.commentAllowed and comment:
        if len(comment) > res.commentAllowed:
            raise LnurlResponseException(f"Comment length {len(comment)} exceeds allowed length {res.commentAllowed}")
        params["comment"] = comment

    try:
        proxy = tor_socks or TOR_SOCKS if res.callback.host and res.callback.host.endswith(".onion") else None
        async with _http_client(client, user_agent=user_agent, proxy=proxy, timeout=timeout) as http_client:
            try:
                res2 = await http_client.get(
                    url=str(res.callback),
                    params=params,
                )
                res2.raise_for_status()
            except httpx.ConnectError as exc:
                if proxy:
                    raise LnurlResponseException(
                        f"Failed to connect to {res.callback!s} via Tor proxy {proxy}. Is Tor running?"
                    ) from exc
                raise LnurlResponseException(f"Failed to connect to {res.callback!s}") from exc
            except Exception as exc:
                raise LnurlResponseException(str(exc))

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
    tor_socks: Optional[str] = None,
    *,
    client: Optional[httpx.AsyncClient] = None,
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
    key, sig = lnurlauth_signature(res.k1, linking_key=linking_key)
    proxy = tor_socks or TOR_SOCKS if res.callback.host and res.callback.host.endswith(".onion") else None
    async with _http_client(client, user_agent=user_agent, proxy=proxy, timeout=timeout) as http_client:
        try:
            res2 = await http_client.get(
                url=str(res.callback),
                params={
                    "key": key,
                    "sig": sig,
                },
            )
            res2.raise_for_status()
        except httpx.ConnectError as exc:
            if proxy:
                raise LnurlResponseException(
                    f"Failed to connect to {res.callback!s} via Tor proxy {proxy}. Is Tor running?"
                ) from exc
            raise LnurlResponseException(f"Failed to connect to {res.callback!s}") from exc
        except Exception as e:
            raise LnurlResponseException(str(e))

        return LnurlResponse.from_dict(res2.json())


async def execute_withdraw(
    res: LnurlWithdrawResponse,
    pr: str,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
    tor_socks: Optional[str] = None,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> LnurlSuccessResponse:
    try:
        invoice = bolt11_decode(pr)
    except Bolt11Exception as exc:
        raise LnurlResponseException(str(exc))
    # if invoice does not have amount use the min withdrawable amount
    amount = invoice.amount_msat or res.minWithdrawable
    if not res.minWithdrawable <= MilliSatoshi(amount) <= res.maxWithdrawable:
        raise LnurlResponseException(f"Amount {amount} not in range {res.minWithdrawable} - {res.maxWithdrawable}")
    proxy = tor_socks or TOR_SOCKS if res.callback.host and res.callback.host.endswith(".onion") else None
    async with _http_client(client, user_agent=user_agent, proxy=proxy, timeout=timeout) as http_client:
        try:
            res2 = await http_client.get(
                url=str(res.callback),
                params={
                    "k1": res.k1,
                    "pr": pr,
                },
            )
            res2.raise_for_status()
        except httpx.ConnectError as exc:
            if proxy:
                raise LnurlResponseException(
                    f"Failed to connect to {res.callback!s} via Tor proxy {proxy}. Is Tor running?"
                ) from exc
            raise LnurlResponseException(f"Failed to connect to {res.callback!s}") from exc
        except Exception as exc:
            raise LnurlResponseException(str(exc))
        withdraw_res = LnurlResponse.from_dict(res2.json())
        if isinstance(withdraw_res, LnurlErrorResponse):
            raise LnurlResponseException(withdraw_res.reason)
        if not isinstance(withdraw_res, LnurlSuccessResponse):
            raise LnurlResponseException(f"Expected LnurlSuccessResponse, got {type(withdraw_res)}")
        return withdraw_res


# LUD-23: addressRequest base spec.
async def execute_address_request(
    res: LnurlAddressRequestResponse,
    address: str,
    user_agent: Optional[str] = None,
    timeout: Optional[int] = None,
    tor_socks: Optional[str] = None,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> LnurlResponseModel:
    try:
        lnaddress = LnAddress(address)
    except (ValidationError, ValueError, LnAddressError) as exc:
        raise LnurlResponseException("Invalid Lightning address.") from exc

    proxy = tor_socks or TOR_SOCKS if res.callback.host and res.callback.host.endswith(".onion") else None
    async with _http_client(client, user_agent=user_agent, proxy=proxy, timeout=timeout) as http_client:
        try:
            res2 = await http_client.get(
                url=str(res.callback),
                params={
                    "k1": res.k1,
                    "address": lnaddress.address,
                },
            )
            res2.raise_for_status()
        except httpx.ConnectError as exc:
            if proxy:
                raise LnurlResponseException(
                    f"Failed to connect to {res.callback!s} via Tor proxy {proxy}. Is Tor running?"
                ) from exc
            raise LnurlResponseException(f"Failed to connect to {res.callback!s}") from exc
        except Exception as exc:
            raise LnurlResponseException(str(exc))
        address_res = LnurlResponse.from_dict(res2.json())
        if isinstance(address_res, LnurlErrorResponse):
            raise LnurlResponseException(address_res.reason)
        if not isinstance(address_res, LnurlSuccessResponse):
            raise LnurlResponseException(f"Expected LnurlSuccessResponse, got {type(address_res)}")
        return address_res
