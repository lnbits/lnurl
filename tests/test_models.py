import json
import pytest

from pydantic import ValidationError

from lnurl.models import (
    LnurlErrorResponse,
    LnurlSuccessResponse,
    LnurlChannelResponse,
    LnurlHostedChannelResponse,
    LnurlPayResponse,
    LnurlWithdrawResponse,
)


class TestLnurlErrorResponse:
    def test_response(self):
        res = LnurlErrorResponse(reason="blah blah blah")
        assert res.ok is False
        assert res.error_msg == "blah blah blah"
        assert res.json() == '{"status": "ERROR", "reason": "blah blah blah"}'
        assert res.dict() == {"status": "ERROR", "reason": "blah blah blah"}

    def test_no_reason(self):
        with pytest.raises(ValidationError):
            LnurlErrorResponse()


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
        assert res.dict() == {**{"tag": "hostedChannelRequest", "alias": None}, **d}

    @pytest.mark.parametrize(
        "d", [{"uri": "invalid", "k1": "c3RyaW5n"}, {"uri": "node_key@ip_address:port_number", "k1": None}]
    )
    def test_invalid_data(self, d):
        with pytest.raises(ValidationError):
            LnurlHostedChannelResponse(**d)


metadata = '[["text/plain","lorem ipsum blah blah"]]'


class TestLnurlPayResponse:
    @pytest.mark.parametrize(
        "d",
        [
            {"callback": "https://service.io/pay", "min_sendable": 1000, "max_sendable": 2000, "metadata": metadata},
            {"callback": "https://service.io/pay", "minSendable": 1000, "maxSendable": 2000, "metadata": metadata},
        ],
    )
    def test_success_response(self, d):
        res = LnurlPayResponse(**d)
        assert res.ok
        assert (
            res.json()
            == res.json(by_alias=True)
            == (
                f'{{"tag": "payRequest", "callback": "https://service.io/pay", '
                f'"minSendable": 1000, "maxSendable": 2000, "metadata": {json.dumps(metadata)}}}'
            )
        )
        assert (
            res.dict()
            == res.dict(by_alias=True)
            == {
                "tag": "payRequest",
                "callback": "https://service.io/pay",
                "minSendable": 1000,
                "maxSendable": 2000,
                "metadata": metadata,
            }
        )
        assert res.dict(by_alias=False) == {
            "tag": "payRequest",
            "callback": "https://service.io/pay",
            "min_sendable": 1000,
            "max_sendable": 2000,
            "metadata": metadata,
        }

    @pytest.mark.parametrize(
        "d",
        [
            {"callback": "invalid", "min_sendable": 1000, "max_sendable": 2000, "metadata": metadata},
            {"callback": "https://service.io/pay"},  # missing fields
            {"callback": "https://service.io/pay", "min_sendable": 0, "max_sendable": 0, "metadata": metadata},  # 0
            {"callback": "https://service.io/pay", "minSendable": 100, "maxSendable": 10, "metadata": metadata},  # max
            {"callback": "https://service.io/pay", "minSendable": -90, "maxSendable": -10, "metadata": metadata},
        ],
    )
    def test_invalid_data(self, d):
        with pytest.raises(ValidationError):
            LnurlPayResponse(**d)


class TestLnurlWithdrawResponse:
    @pytest.mark.parametrize(
        "d",
        [
            {
                "callback": "https://service.io/withdraw",
                "k1": "c3RyaW5n",
                "min_withdrawable": 100,
                "max_withdrawable": 200,
            },
            {
                "callback": "https://service.io/withdraw",
                "k1": "c3RyaW5n",
                "minWithdrawable": 100,
                "maxWithdrawable": 200,
            },
        ],
    )
    def test_success_response(self, d):
        res = LnurlWithdrawResponse(**d)
        assert res.ok
        assert (
            res.json()
            == res.json(by_alias=True)
            == (
                '{"tag": "withdrawRequest", "callback": "https://service.io/withdraw", "k1": "c3RyaW5n", '
                '"minWithdrawable": 100, "maxWithdrawable": 200, "defaultDescription": ""}'
            )
        )
        assert (
            res.dict()
            == res.dict(by_alias=True)
            == {
                "tag": "withdrawRequest",
                "callback": "https://service.io/withdraw",
                "k1": "c3RyaW5n",
                "minWithdrawable": 100,
                "maxWithdrawable": 200,
                "defaultDescription": "",
            }
        )
        assert res.dict(by_alias=False) == {
            "tag": "withdrawRequest",
            "callback": "https://service.io/withdraw",
            "k1": "c3RyaW5n",
            "min_withdrawable": 100,
            "max_withdrawable": 200,
            "default_description": "",
        }

    @pytest.mark.parametrize(
        "d",
        [
            {"callback": "invalid", "k1": "c3RyaW5n", "min_withdrawable": 1000, "max_withdrawable": 2000},
            {"callback": "https://service.io/withdraw", "k1": "c3RyaW5n"},  # missing fields
            {"callback": "https://service.io/withdraw", "k1": "c3RyaW5n", "min_withdrawable": 0, "max_withdrawable": 0},
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
