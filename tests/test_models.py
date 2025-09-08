import json

import pytest
from pydantic import ValidationError, parse_obj_as

from lnurl import CallbackUrl, Lnurl, LnurlPayMetadata, MilliSatoshi, encode
from lnurl.models import (
    LnurlChannelResponse,
    LnurlErrorResponse,
    LnurlHostedChannelResponse,
    LnurlPayResponse,
    LnurlSuccessResponse,
    LnurlWithdrawResponse,
)


class TestLnurlErrorResponse:
    def test_response(self):
        res = LnurlErrorResponse(reason="blah blah blah")
        assert res.ok is False
        assert res.error_msg == "blah blah blah"
        assert res.json() == '{"status": "ERROR", "reason": "blah blah blah"}'
        assert res.dict() == {"status": "ERROR", "reason": "blah blah blah"}


class TestLnurlSuccessResponse:
    def test_success_response(self):
        res = LnurlSuccessResponse()
        assert res.ok
        assert res.json() == '{"status": "OK"}'
        assert res.dict() == {"status": "OK"}


class TestLnurlChannelResponse:
    @pytest.mark.parametrize(
        "d", [{"uri": "node_key@ip_address:port_number", "callback": "https://service.io/channel", "k1": "c3RyaW5n"}]
    )
    def test_channel_response(self, d):
        res = LnurlChannelResponse(**d)
        assert res.ok
        assert res.dict() == {**{"tag": "channelRequest"}, **d}

    @pytest.mark.parametrize(
        "d",
        [
            {"uri": "invalid", "callback": "https://service.io/channel", "k1": "c3RyaW5n"},
            {"uri": "node_key@ip_address:port_number", "callback": "invalid", "k1": "c3RyaW5n"},
            {"uri": "node_key@ip_address:port_number", "callback": "https://service.io/channel", "k1": None},
        ],
    )
    def test_invalid_data(self, d):
        with pytest.raises(ValidationError):
            LnurlChannelResponse(**d)


class TestLnurlHostedChannelResponse:
    @pytest.mark.parametrize("d", [{"uri": "node_key@ip_address:port_number", "k1": "c3RyaW5n"}])
    def test_channel_response(self, d):
        res = LnurlHostedChannelResponse(**d)
        assert res.ok
        assert res.dict() == {**{"tag": "hostedChannelRequest"}, **d}

    @pytest.mark.parametrize(
        "d", [{"uri": "invalid", "k1": "c3RyaW5n"}, {"uri": "node_key@ip_address:port_number", "k1": None}]
    )
    def test_invalid_data(self, d):
        with pytest.raises(ValidationError):
            LnurlHostedChannelResponse(**d)


metadata = '[["text/plain","lorem ipsum blah blah"]]'


class TestLnurlPayResponse:
    @pytest.mark.parametrize(
        "callback, min_sendable, max_sendable, metadata",
        [
            (
                "https://service.io/pay",
                1000,
                2000,
                metadata,
            ),
        ],
    )
    def test_success_response(self, callback: str, min_sendable: int, max_sendable: int, metadata: str):
        callback_url = parse_obj_as(CallbackUrl, callback)
        data = parse_obj_as(LnurlPayMetadata, metadata)
        res = LnurlPayResponse(
            callback=callback_url,
            minSendable=MilliSatoshi(min_sendable),
            maxSendable=MilliSatoshi(max_sendable),
            metadata=data,
        )
        assert res.ok
        assert (
            res.json() == res.json() == '{"tag": "payRequest", "callback": "https://service.io/pay", '
            f'"minSendable": 1000, "maxSendable": 2000, "metadata": {json.dumps(metadata)}}}'
        )
        assert (
            res.dict()
            == res.dict()
            == {
                "tag": "payRequest",
                "callback": "https://service.io/pay",
                "minSendable": 1000,
                "maxSendable": 2000,
                "metadata": metadata,
            }
        )

    @pytest.mark.parametrize(
        "d",
        [
            {"callback": "invalid", "minSendable": 1000, "maxSendable": 2000, "metadata": metadata},
            {"callback": "https://service.io/pay"},  # missing fields
            {"callback": "https://service.io/pay", "minSendable": 0, "maxSendable": 0, "metadata": metadata},  # 0
            {"callback": "https://service.io/pay", "minSendable": 100, "maxSendable": 10, "metadata": metadata},  # max
            {"callback": "https://service.io/pay", "minSendable": -90, "maxSendable": -10, "metadata": metadata},
        ],
    )
    def test_invalid_data(self, d):
        with pytest.raises(ValidationError):
            LnurlPayResponse(**d)


class TestLnurlPayResponseComment:
    @pytest.mark.parametrize(
        "callback, min_sendable, max_sendable, metadata, comment_allowed",
        [
            (
                "https://service.io/pay",
                1000,
                2000,
                metadata,
                555,  # comment allowed
            ),
        ],
    )
    def test_success_response(
        self, callback: str, min_sendable: int, max_sendable: int, metadata: str, comment_allowed: int
    ):
        res = LnurlPayResponse(
            callback=parse_obj_as(CallbackUrl, callback),
            minSendable=MilliSatoshi(min_sendable),
            maxSendable=MilliSatoshi(max_sendable),
            metadata=parse_obj_as(LnurlPayMetadata, metadata),
            commentAllowed=comment_allowed,
        )
        assert res.ok
        assert (
            res.json() == res.json() == '{"tag": "payRequest", "callback": "https://service.io/pay", '
            f'"minSendable": 1000, "maxSendable": 2000, "metadata": {json.dumps(metadata)}, '
            '"commentAllowed": 555}'
        )
        assert (
            res.dict()
            == res.dict()
            == {
                "tag": "payRequest",
                "callback": "https://service.io/pay",
                "minSendable": 1000,
                "maxSendable": 2000,
                "metadata": metadata,
                "commentAllowed": 555,
            }
        )

    @pytest.mark.parametrize(
        "d",
        [
            {"callback": "invalid", "minSendable": 1000, "maxSendable": 2000, "metadata": metadata},
            {"callback": "https://service.io/pay"},  # missing fields
            {"callback": "https://service.io/pay", "minSendable": 0, "maxSendable": 0, "metadata": metadata},  # 0
            {"callback": "https://service.io/pay", "minSendable": 100, "maxSendable": 10, "metadata": metadata},  # max
            {"callback": "https://service.io/pay", "minSendable": -90, "maxSendable": -10, "metadata": metadata},
            {
                "callback": "https://service.io/pay",
                "minSendable": 100,
                "maxSendable": 1000,
                "metadata": metadata,
                "commentAllowed": "Yes",  # str should be int
            },
        ],
    )
    def test_invalid_data(self, d):
        with pytest.raises(ValidationError):
            LnurlPayResponse(**d)


class TestLnurlWithdrawResponse:
    @pytest.mark.parametrize(
        "callback, k1, min_withdrawable, max_withdrawable",
        [
            (
                "https://service.io/withdraw",
                "c3RyaW5n",
                100,
                200,
            ),
        ],
    )
    def test_success_response(self, callback: str, k1: str, min_withdrawable: int, max_withdrawable: int):
        res = LnurlWithdrawResponse(
            callback=parse_obj_as(CallbackUrl, callback),
            k1=k1,
            minWithdrawable=MilliSatoshi(min_withdrawable),
            maxWithdrawable=MilliSatoshi(max_withdrawable),
        )
        assert res.ok
        assert (
            res.json()
            == res.json()
            == '{"tag": "withdrawRequest", "callback": "https://service.io/withdraw", "k1": "c3RyaW5n", '
            '"minWithdrawable": 100, "maxWithdrawable": 200, "defaultDescription": ""}'
        )
        assert (
            res.dict()
            == res.dict()
            == {
                "tag": "withdrawRequest",
                "callback": "https://service.io/withdraw",
                "k1": "c3RyaW5n",
                "minWithdrawable": 100,
                "maxWithdrawable": 200,
                "defaultDescription": "",
            }
        )

    @pytest.mark.parametrize(
        "d",
        [
            {"callback": "invalid", "k1": "c3RyaW5n", "minWithdrawable": 1000, "maxWithdrawable": 2000},
            {"callback": "https://service.io/withdraw", "k1": "c3RyaW5n"},  # missing fields
            {
                "callback": "https://service.io/withdraw",
                "k1": "c3RyaW5n",
                "minWithdrawable": 100,
                "maxWithdrawable": 10,
            },
            {"callback": "https://service.io/withdraw", "k1": "c3RyaW5n", "minWithdrawable": -9, "maxWithdrawable": -1},
        ],
    )
    def test_invalid_data(self, d):
        with pytest.raises(ValidationError):
            LnurlWithdrawResponse(**d)

    @pytest.mark.parametrize(
        "payLink",
        [
            "https://service.io/withdraw",
            "lnurlw://service.io/withdraw",  # wrong LUD17
            str(encode("https://service.io/withdraw").bech32),  # bech32
        ],
    )
    def test_invalid_pay_link(self, payLink: str):
        with pytest.raises(ValidationError):
            _ = LnurlWithdrawResponse(
                callback=parse_obj_as(CallbackUrl, "https://service.io/withdraw/cb"),
                k1="c3RyaW5n",
                minWithdrawable=MilliSatoshi(100),
                maxWithdrawable=MilliSatoshi(200),
                payLink=payLink,
            )

    def test_valid_pay_link(self):
        payLink = parse_obj_as(Lnurl, "lnurlp://service.io/pay")
        assert payLink.is_lud17
        assert payLink.lud17_prefix == "lnurlp"
        _ = LnurlWithdrawResponse(
            callback=parse_obj_as(CallbackUrl, "https://service.io/withdraw/cb"),
            k1="c3RyaW5n",
            minWithdrawable=MilliSatoshi(100),
            maxWithdrawable=MilliSatoshi(200),
            payLink=payLink.lud17,
        )
