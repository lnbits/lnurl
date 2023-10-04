from typing import Union

import pytest
from pydantic import TypeAdapter, ValidationError

from lnurl.helpers import _lnurl_clean
from lnurl.types import (
    ClearnetUrl,
    DebugUrl,
    LightningInvoice,
    LightningNodeUri,
    Lnurl,
    LnurlPayMetadata,
    OnionUrl,
)


class TestUrl:
    # https://github.com/pydantic/pydantic/discussions/2450
    @pytest.mark.parametrize(
        "hostport",
        ["service.io:443", "service.io:9000"],
    )
    def test_parameters(self, hostport):
        adapter = TypeAdapter(Union[DebugUrl, OnionUrl, ClearnetUrl])
        url = adapter.validate_python(f"https://{hostport}/?q=3fc3645b439ce8e7&test=ok")
        assert url.host == "service.io"
        # assert url.base == f"https://{hostport}/"
        assert url.query_params() == [
            (
                "q",
                "3fc3645b439ce8e7",
            ),
            (
                "test",
                "ok",
            ),
        ]

    @pytest.mark.parametrize(
        "url",
        [
            "https://service.io/?q=3fc3645b439ce8e7&test=ok",
            "https://[2001:db8:0:1]:80",
            "https://protonirockerxow.onion/",
            "http://protonirockerxow.onion/",
            "https://📙.la/⚡",  # https://emojipedia.org/high-voltage-sign/
            "https://xn--yt8h.la/%E2%9A%A1",
            "http://0.0.0.0",
            "http://127.0.0.1",
        ],
    )
    def test_valid(self, url):
        adapter = TypeAdapter(Union[DebugUrl, OnionUrl, ClearnetUrl])
        url = adapter.validate_python(url)
        assert isinstance(url, (OnionUrl, DebugUrl, ClearnetUrl))

    @pytest.mark.parametrize(
        "url",
        [
            "http://service.io/?q=3fc3645b439ce8e7&test=ok",
            "http://[2001:db8:0:1]:80",
            f'https://service.io/?hash={"x" * 4096}',
            "https://1.1.1.1/\u0000",
            "http://xn--yt8h.la/%E2%9A%A1",
            "http://1.1.1.1",
        ],
    )
    def test_invalid_data(self, url):
        with pytest.raises(ValidationError):
            adapter = TypeAdapter(Union[DebugUrl, OnionUrl, ClearnetUrl])
            adapter.validate_python(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://📙.la/⚡",  # https://emojipedia.org/high-voltage-sign/
            "https://xn--yt8h.la/%E2%9A%A1",
        ],
    )
    def test_strict_rfc3986(self, monkeypatch, url):
        monkeypatch.setenv("LNURL_STRICT_RFC3986", "1")
        with pytest.raises(ValidationError):
            adapter = TypeAdapter(ClearnetUrl)
            adapter.validate_python(url)


class TestLightningInvoice:
    @pytest.mark.xfail(raises=NotImplementedError)
    @pytest.mark.parametrize(
        "bech32, hrp, prefix, amount, h",
        [
            (
                (
                    "lntb20m1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqhp58yjmdan79s6qqdhdzgynm4zwqd"
                    "5d7xmw5fk98klysy043l2ahrqsfpp3x9et2e20v6pu37c5d9vax37wxq72un98k6vcx9fz94w0qf237cm2rqv9pmn5lnexfvf55"
                    "79slr4zq3u8kmczecytdx0xg9rwzngp7e6guwqpqlhssu04sucpnz4axcv2dstmknqq6jsk2l"
                ),
                "lntb20m",
                "lntb",
                20,
                "h",
            ),
        ],
    )
    def test_valid(self, bech32, hrp, prefix, amount, h):
        invoice = LightningInvoice(bech32)
        adapter = TypeAdapter(LightningInvoice)
        assert invoice == adapter.validate_python(bech32)
        assert invoice.hrp == hrp
        assert invoice.prefix == prefix
        assert invoice.amount == amount
        assert invoice.h == h


class TestLightningNode:
    def test_valid(self):
        adapter = TypeAdapter(LightningNodeUri)
        node = adapter.validate_python("node_key@ip_address:port_number")
        assert node.key == "node_key"
        assert node.ip == "ip_address"
        assert node.port == "port_number"

    @pytest.mark.parametrize("uri", ["https://service.io/node", "node_key@ip_address", "ip_address:port_number"])
    def test_invalid_data(self, uri):
        with pytest.raises(ValidationError):
            adapter = TypeAdapter(LightningNodeUri)
            adapter.validate_python(uri)


class TestLnurl:
    @pytest.mark.parametrize(
        "lightning, url",
        [
            (
                (
                    "LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K"
                    "XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU"
                ),
                "https://service.io/?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df",
            ),
            (
                (
                    "lightning:LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K"
                    "XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU"
                ),
                "https://service.io/?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df",
            ),
        ],
    )
    def test_valid(self, lightning, url):
        lnurl = Lnurl(lightning)
        adapter = TypeAdapter(Lnurl)
        assert lnurl == lnurl.bech32 == _lnurl_clean(lightning) == adapter.validate_python(lightning)
        assert lnurl.bech32.hrp == "lnurl"
        assert lnurl.url == url
        # assert lnurl.url.base == "https://service.io:443/"
        assert lnurl.url.query_params == {"q": "3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df"}
        assert lnurl.is_login is False

    @pytest.mark.parametrize(
        "bech32",
        [
            "abcdef1qpzry9x8gf2tvdw0s3jn54khce6mua7lmqqqxw",
            "split1checkupstagehandshakeupstreamerranterredcaperred2y9e3w",
            "BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4",
        ],
    )
    def test_decode_nolnurl(self, bech32):
        with pytest.raises(ValidationError):
            adapter = TypeAdapter(Lnurl)
            adapter.validate_python(bech32)


class TestLnurlPayMetadata:
    @pytest.mark.parametrize(
        "metadata, image_type",
        [
            ('[["text/plain", "main text"]]', None),
            ('[["text/plain", "main text"], ["image/jpeg;base64", "base64encodedimage"]]', "jpeg"),
            ('[["text/plain", "main text"], ["image/png;base64", "base64encodedimage"]]', "png"),
        ],
    )
    def test_valid(self, metadata, image_type):
        adapter = TypeAdapter(LnurlPayMetadata)
        m = adapter.validate_python(metadata)

        assert m.text == "main text"

        if m.images:
            assert len(m.images) == 1
            assert dict(m.images)[f"image/{image_type};base64"] == "base64encodedimage"

    @pytest.mark.parametrize(
        "metadata",
        [
            "[]",
            '["text""plain"]',
            '[["text", "plain"]]',
            '[["text", "plain", "plane"]]',
            '[["text/plain", "main text"], ["text/plain", "two is too much"]]',
            '[["image/jpeg;base64", "base64encodedimage"]]',
        ],
    )
    def test_invalid_data(self, metadata):
        with pytest.raises(ValidationError):
            adapter = TypeAdapter(LnurlPayMetadata)
            adapter.validate_python(metadata)
