import httpx
import pytest

from lnurl.core import decode, encode, execute_login, execute_pay_request, get, handle
from lnurl.exceptions import InvalidLnurl, InvalidUrl, LnurlResponseException
from lnurl.models import (
    LnurlAuthResponse,
    LnurlPayActionResponse,
    LnurlPayResponse,
    LnurlPaySuccessAction,
    LnurlSuccessResponse,
    LnurlWithdrawResponse,
)
from lnurl.types import Lnurl, Url


class TestDecode:
    @pytest.mark.parametrize(
        "bech32, url",
        [
            (
                (
                    "LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K"
                    "XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU"
                ),
                "https://service.io/?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df",
            )
        ],
    )
    def test_decode(self, bech32, url):
        decoded_url = decode(bech32)
        assert isinstance(decoded_url, Url)
        assert decoded_url == str(decoded_url) == url
        assert decoded_url.host == "service.io"

    @pytest.mark.parametrize(
        "bech32",
        [
            "abcdef1qpzry9x8gf2tvdw0s3jn54khce6mua7lmqqqxw",
            "split1checkupstagehandshakeupstreamerranterredcaperred2y9e3w",
            "BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4",
        ],
    )
    def test_decode_nolnurl(self, bech32):
        with pytest.raises(InvalidLnurl):
            decode(bech32)


class TestEncode:
    @pytest.mark.parametrize(
        "bech32, url",
        [
            (
                (
                    "LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K"
                    "XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU"
                ),
                "https://service.io/?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df",
            )
        ],
    )
    def test_encode(self, bech32, url):
        lnurl = encode(url)
        assert isinstance(lnurl, Lnurl)
        assert lnurl.bech32 == bech32
        assert lnurl.url.host == "service.io"

    @pytest.mark.parametrize("url", ["http://service.io/"])
    def test_encode_nohttps(self, url):
        with pytest.raises(InvalidUrl):
            encode(url)


class TestHandle:
    """Responses from the LNURL: https://demo.lnbits.com/"""

    @pytest.mark.xfail(reason="legend.lnbits.com is down")
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bech32",
        [
            "LNURL1DP68GURN8GHJ7MR9VAJKUEPWD3HXY6T5WVHXXMMD9AMKJARGV3EXZAE0V9CXJTMKXYH"
            "KCMN4WFKZ7MJT2C6X2NRK0PDRYJNGWVU9WDN2G4V8XK2VSZA2RC"
        ],
    )
    async def test_handle_withdraw(self, bech32):
        res = await handle(bech32)
        assert isinstance(res, LnurlWithdrawResponse)
        assert res.tag == "withdrawRequest"
        assert res.callback.host == "demo.lnbits.com"
        assert res.default_description == "sample withdraw"
        assert res.max_withdrawable >= res.min_withdrawable

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bech32", ["BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4"])
    async def test_handle_nolnurl(self, bech32):
        with pytest.raises(InvalidLnurl):
            await handle(bech32)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("url", ["https://lnurl.thisshouldfail.io/"])
    async def test_get_requests_error(self, url):
        with pytest.raises(LnurlResponseException):
            await get(url)


class TestPayFlow:
    """Full LNURL-pay flow interacting with https://demo.lnbits.com/"""

    @pytest.mark.xfail(reason="legend.lnbits.com is down")
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bech32, amount",
        [
            (
                "LNURL1DP68GURN8GHJ7MR9VAJKUEPWD3HXY6T5WVHXXMMD9AKXUATJD3CZ7JN9F4EHQJQC25ZZY",
                "1000",
            ),
            ("donate@demo.lnbits.com", "100000"),
        ],
    )
    async def test_pay_flow(self, bech32: str, amount: str):
        res = await handle(bech32)
        assert isinstance(res, LnurlPayResponse)
        assert res.tag == "payRequest"
        assert res.callback.host == "demo.lnbits.com"
        assert len(res.metadata.list()) >= 1
        assert res.metadata.text != ""

        res2 = await execute_pay_request(res, amount)
        assert isinstance(res2, LnurlPayActionResponse)
        assert res2.success_action is None or isinstance(res2.success_action, LnurlPaySuccessAction)


class TestLoginFlow:
    """Full LNURL-login flow interacting with https://lnmarkets.com/"""

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="need online lnurl auth server to test this flow")
    @pytest.mark.parametrize(
        "url",
        [
            "https://api.lnmarkets.com/trpc/lnurl.auth.new",
        ],
    )
    async def test_login_flow(self, url: str):
        async with httpx.AsyncClient() as client:
            init = await client.get(url)
            init.raise_for_status()
            bech32 = init.json()["result"]["data"]["json"]["lnurl"]

            res = await handle(bech32)
            assert isinstance(res, LnurlAuthResponse)
            assert res.tag == "login"
            assert res.callback.host == "api.lnmarkets.com"

            res2 = await execute_login(res, "my-secret")
            assert isinstance(res2, LnurlSuccessResponse)
