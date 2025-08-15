import pytest
from pydantic import ValidationError, parse_obj_as

from lnurl import (
    CallbackUrl,
    LightningInvoice,
    LightningNodeUri,
    LnAddress,
    LnAddressError,
    Lnurl,
    LnurlErrorResponse,
    LnurlPayerData,
    LnurlPayerDataAuth,
    LnurlPayMetadata,
    LnurlPayResponsePayerData,
    LnurlPayResponsePayerDataExtra,
    LnurlPayResponsePayerDataOption,
    LnurlPayResponsePayerDataOptionAuth,
)


class TestUrl:
    # https://github.com/pydantic/pydantic/discussions/2450
    @pytest.mark.parametrize(
        "hostport",
        ["service.io:443", "service.io:9000"],
    )
    def test_parameters(self, hostport):
        url = parse_obj_as(CallbackUrl, f"https://{hostport}/?q=3fc3645b439ce8e7&test=ok")
        assert url.host == "service.io"
        assert url == f"https://{hostport}/?q=3fc3645b439ce8e7&test=ok"
        assert url.query_params == {"q": "3fc3645b439ce8e7", "test": "ok"}

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
            "http://localhost",
        ],
    )
    def test_valid_callback(self, url):
        url = parse_obj_as(CallbackUrl, url)
        assert isinstance(url, CallbackUrl)

    @pytest.mark.parametrize(
        "url",
        [
            "http://service.io/?q=3fc3645b439ce8e7&test=ok",
            "http://[2001:db8:0:1]:80",
            f'https://service.io/?hash={"x" * 4096}',
            "https://1.1.1.1/\u0000",
            "http://xn--yt8h.la/%E2%9A%A1",
            "http://1.1.1.1",
            "lnurlp://service.io",
        ],
    )
    def test_invalid_data_callback(self, url):
        with pytest.raises(ValidationError):
            parse_obj_as(CallbackUrl, url)

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
            parse_obj_as(CallbackUrl, url)


class TestLightningInvoice:
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
    def test_valid_invoice(self, bech32, hrp, prefix, amount, h):
        invoice = LightningInvoice(bech32)
        assert invoice == parse_obj_as(LightningInvoice, bech32)
        assert invoice.hrp == hrp
        # TODO: implement these properties
        # assert invoice.prefix == prefix
        # assert invoice.amount == amount


class TestLightningNode:
    def test_valid_node(self):
        node = parse_obj_as(LightningNodeUri, "node_key@ip_address:port_number")
        assert node.key == "node_key"
        assert node.ip == "ip_address"
        assert node.port == "port_number"

    @pytest.mark.parametrize("uri", ["https://service.io/node", "node_key@ip_address", "ip_address:port_number"])
    def test_invalid_node(self, uri):
        with pytest.raises(ValidationError):
            parse_obj_as(LightningNodeUri, uri)


class TestLnurl:
    @pytest.mark.parametrize(
        "lightning",
        [
            (
                "LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K"
                "XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU"
            ),
            (
                "lightning:LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K"
                "XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU"
            ),
            "https://service.io?a=1&b=2",
            "lnurlp://service.io?a=1&b=2",
        ],
    )
    def test_valid_lnurl_and_bech32(self, lightning):
        lnurl = Lnurl(lightning)
        assert lnurl == parse_obj_as(Lnurl, lightning)
        if lnurl.is_lud17:
            assert lnurl.lud17 == lightning
            assert lnurl.lud17_prefix == lightning.split("://")[0]
            assert lnurl.is_lud17 is True
            assert lnurl.url == lightning.replace("lnurlp://", "https://")
            assert lnurl == lightning.replace("lnurlp://", "https://")
        else:
            assert lnurl.bech32 is not None
            assert lnurl.bech32.hrp == "lnurl"
            assert lnurl.bech32 == lnurl or lnurl.url == lnurl
            assert lnurl.lud17 is None
            assert lnurl.lud17_prefix is None
            assert lnurl.is_lud17 is False

        assert lnurl.is_login is False

    @pytest.mark.parametrize(
        "url",
        [
            "lnurlp://service.io?a=1&b=2",
            "lnurlc://service.io",
            "lnurlw://service.io",
            "keyauth://service.io",
        ],
    )
    def test_valid_lnurl_lud17(self, url: str):
        _lnurl = parse_obj_as(Lnurl, url)

        _prefix = url.split("://")[0]
        assert _lnurl.lud17 == url
        assert _lnurl.lud17_prefix == _prefix
        assert _lnurl.is_lud17 is True
        _url = url.replace("lnurlp://", "https://")
        _url = _url.replace("lnurlc://", "https://")
        _url = _url.replace("lnurlw://", "https://")
        _url = _url.replace("keyauth://", "https://")
        assert str(_lnurl.url) == _url
        assert str(_lnurl) == _url

    @pytest.mark.parametrize(
        "url",
        [
            "http://service.io",
            "lnurlx://service.io",
        ],
    )
    def test_invalid_lnurl(self, url: str):
        with pytest.raises(ValidationError):
            parse_obj_as(Lnurl, url)

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
            parse_obj_as(Lnurl, bech32)


class TestLnurlPayMetadata:
    @pytest.mark.parametrize(
        "metadata, image_type",
        [
            ('[["text/plain", "main text"]]', None),
            ('[["text/plain", "main text"], ["image/jpeg;base64", "base64encodedimage"]]', "jpeg"),
            ('[["text/plain", "main text"], ["image/png;base64", "base64encodedimage"]]', "png"),
            ('[["text/plain", "main text"], ["text/indentifier", "alan@lnbits.com"], ["text/tag", "tag"]]', None),
        ],
    )
    def test_valid(self, metadata, image_type):
        m = parse_obj_as(LnurlPayMetadata, metadata)
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
            parse_obj_as(LnurlPayMetadata, metadata)

    @pytest.mark.parametrize(
        "lnaddress",
        [
            "donate@legend.lnbits.com",
        ],
    )
    def test_valid_lnaddress(self, lnaddress):
        lnaddress = LnAddress(lnaddress)
        assert isinstance(lnaddress.url, CallbackUrl)
        assert lnaddress.tag is None

    @pytest.mark.parametrize(
        "lnaddress",
        [
            "donate+lud16tag@legend.lnbits.com",
        ],
    )
    def test_valid_lnaddress_with_tag(self, lnaddress):
        lnaddress = LnAddress(lnaddress)
        assert isinstance(lnaddress.url, CallbackUrl)
        assert lnaddress.tag == "lud16tag"

    @pytest.mark.parametrize(
        "lnaddress",
        [
            "legend.lnbits.com",
            "donate@donate@legend.lnbits.com",
            "HELLO@lnbits.com",
        ],
    )
    def test_invalid_lnaddress(self, lnaddress):
        with pytest.raises(LnAddressError):
            lnaddress = LnAddress(lnaddress)


class TestPayerData:

    def test_valid_pay_response_payer_data(self):
        data = {
            "name": {"mandatory": True},
            "pubkey": {"mandatory": True},
            "auth": {"mandatory": True, "k1": "0" * 32},
            "extras": [
                {
                    "name": "extra_field",
                    "field": {"mandatory": True},
                },
            ],
        }
        payer_data = parse_obj_as(LnurlPayResponsePayerData, data)
        assert payer_data.name is not None
        assert payer_data.name.mandatory is True
        assert payer_data.pubkey is not None
        assert payer_data.pubkey.mandatory is True
        assert payer_data.auth is not None
        assert payer_data.auth.mandatory is True
        assert payer_data.auth.k1 == "0" * 32
        assert payer_data.extras is not None
        assert len(payer_data.extras) == 1
        assert payer_data.extras[0].name == "extra_field"
        assert payer_data.extras[0].field is not None

    def test_valid_pay_response_payer_data_models(self):
        data_option = LnurlPayResponsePayerDataOption(
            mandatory=True,
        )
        payer_data = LnurlPayResponsePayerData(
            name=data_option,
            pubkey=data_option,
            auth=LnurlPayResponsePayerDataOptionAuth(
                mandatory=True,
                k1="0" * 32,
            ),
            extras=[
                LnurlPayResponsePayerDataExtra(
                    name="extra_field",
                    field=LnurlPayResponsePayerDataOption(
                        mandatory=True,
                    ),
                ),
            ],
        )
        assert payer_data.name is not None
        assert payer_data.name.mandatory is True
        assert payer_data.pubkey is not None
        assert payer_data.pubkey.mandatory is True
        assert payer_data.auth is not None
        assert payer_data.auth.mandatory is True
        assert payer_data.auth.k1 == "0" * 32
        assert payer_data.extras is not None
        assert len(payer_data.extras) == 1
        assert payer_data.extras[0].name == "extra_field"
        assert payer_data.extras[0].field is not None

    def test_valid_payer_data(self):
        data = {
            "name": "John Doe",
            "pubkey": "03a3xxxxxxxxxxxx",
            "auth": {
                "key": "key",
                "k1": "0" * 32,
                "sig": "0" * 64,
            },
        }
        payer_data = parse_obj_as(LnurlPayerData, data)
        assert payer_data.name == "John Doe"
        assert payer_data.pubkey == "03a3xxxxxxxxxxxx"
        assert payer_data.auth is not None
        assert payer_data.auth.key == "key"
        assert payer_data.auth.k1 == "0" * 32
        assert payer_data.auth.sig == "0" * 64

    def test_valid_pay_response_payer_model(self):
        data = LnurlPayerData(
            name="John Doe",
            pubkey="03a3xxxxxxxxxxxx",
            auth=LnurlPayerDataAuth(
                key="key",
                k1="0" * 32,
                sig="0" * 64,
            ),
            extras={
                "extra_field": "extra_value",
            },
        )
        assert data.name == "John Doe"
        assert data.pubkey == "03a3xxxxxxxxxxxx"
        assert data.auth is not None
        assert data.auth.key == "key"
        assert data.auth.k1 == "0" * 32
        assert data.auth.sig == "0" * 64
        assert data.extras is not None
        assert data.extras["extra_field"] == "extra_value"


class TestLnurlErrorResponse:
    def test_error_res_details(self):
        res = LnurlErrorResponse(reason="detail")
        _dict = res.dict()
        assert "status" in _dict
        assert _dict["status"] == "ERROR"
        assert "reason" in _dict
        assert _dict["reason"] == "detail"
        assert res.json() == '{"status": "ERROR", "reason": "detail"}'
