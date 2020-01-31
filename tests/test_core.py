import pytest

from urllib.parse import urlencode

from lnurl.core import decode, encode, get, handle
from lnurl.exceptions import LnurlResponseException, InvalidLnurl, InvalidUrl
from lnurl.models import (
    LnurlAuthResponse,
    LnurlPayResponse,
    LnurlPayActionResponse,
    LnurlWithdrawResponse,
    LnurlPaySuccessAction,
)
from lnurl.types import Lnurl, Url


class TestDecode:
    @pytest.mark.parametrize(
        "bech32, url",
        [
            (
                "LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K"
                "XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU",
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
                "LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K"
                "XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU",
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
    """Responses from the LNURL playground: https://lnurl.bigsun.xyz/"""

    @pytest.mark.parametrize(
        "bech32",
        [("LNURL1DP68GURN8GHJ7MRWW4EXCTNZD9NHXATW9EU8J730D3H82UNV94KX7EMFDCLHGCT884KX7EMFDCNXKVFAXUMN2VF4XV6SPQ9K0W")],
    )
    def test_handle_auth(self, bech32):
        res = handle(bech32)
        assert isinstance(res, LnurlAuthResponse)
        assert res.tag == "login"
        assert res.callback.host == "lnurl.bigsun.xyz"
        assert hasattr(res, "k1")

    @pytest.mark.parametrize(
        "bech32",
        [("LNURL1DP68GURN8GHJ7MRWW4EXCTNZD9NHXATW9EU8J730D3H82UNV94MKJARGV3EXZAELWDJHXUMFDAHR6DEHX5CN2VE4K2GN78")],
    )
    def test_handle_withdraw(self, bech32):
        res = handle(bech32)
        assert isinstance(res, LnurlWithdrawResponse)
        assert res.tag == "withdrawRequest"
        assert res.callback.host == "lnurl.bigsun.xyz"
        assert res.default_description == "sample withdraw"
        assert res.max_withdrawable >= res.min_withdrawable

    @pytest.mark.parametrize("bech32", ["BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4"])
    def test_handle_nolnurl(self, bech32):
        with pytest.raises(InvalidLnurl):
            handle(bech32)

    @pytest.mark.parametrize("url", ["https://lnurl.thisshouldfail.io/"])
    def test_get_requests_error(self, url):
        with pytest.raises(LnurlResponseException):
            get(url)


class TestPayFlow:
    """Full LNURL-pay flow interacting with https://lnurl.bigsun.xyz/"""

    @pytest.mark.xfail(raises=NotImplementedError)
    @pytest.mark.parametrize(
        "bech32", [("LNURL1DP68GURN8GHJ7MRWW4EXCTNZD9NHXATW9EU8J730D3H82UNV94CXZ7FLWDJHXUMFDAHR6V3EXYURYDEJSGPG7J")]
    )
    def test_pay_flow(self, bech32):
        res = handle(bech32)
        assert isinstance(res, LnurlPayResponse) is True
        assert res.tag == "payRequest"
        assert res.callback.host == "lnurl.bigsun.xyz"
        assert len(res.metadata.list()) >= 1
        assert res.metadata.text != ""

        query = urlencode({**res.callback.query_params, **{"amount": res.max_sendable}})
        url = "".join([res.callback.base, "?", query])

        res2 = get(url, response_class=LnurlPayActionResponse)
        res3 = get(url)
        assert res2.__class__ == res3.__class__
        assert res2.success_action is None or isinstance(res2.success_action, LnurlPaySuccessAction)
        assert res2.pr.h == res.metadata.h
