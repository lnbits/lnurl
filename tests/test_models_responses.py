import pytest

from pydantic import ValidationError

from lnurl.models.responses import (
    LnurlErrorResponse, LnurlSuccessResponse,
    LnurlChannelResponse, LnurlWithdrawResponse
)


class TestLnurlErrorResponse:

    def test_response(self):
        res = LnurlErrorResponse(reason='blah blah blah')
        assert res.ok is False
        assert res.error_msg == 'blah blah blah'
        assert res.json() == '{"status": "ERROR", "reason": "blah blah blah"}'
        assert res.dict() == {
            'status': 'ERROR',
            'reason': 'blah blah blah'
        }

    def test_no_reason(self):
        with pytest.raises(ValidationError):
            LnurlErrorResponse()


class TestLnurlSuccessResponse:

    def test_success_response(self):
        res = LnurlSuccessResponse()
        assert res.ok is True
        assert res.json() == '{"status": "OK"}'
        assert res.dict() == {
            'status': 'OK'
        }


class TestLnurlChannelResponse:

    @pytest.mark.parametrize('d', [
        {
            'uri': 'node_key@ip_address:port_number',
            'callback': 'https://service.com/channel',
            'k1': 'c3RyaW5n'
        },
    ])
    def test_channel_response(self, d):
        res = LnurlChannelResponse(**d)
        assert res.ok is True
        assert res.dict() == {**{'tag': 'channelRequest'}, **d}

    @pytest.mark.parametrize('d', [
        {'uri': 'invalid', 'callback': 'https://service.com/channel', 'k1': 'c3RyaW5n'},
        {'uri': 'node_key@ip_address:port_number', 'callback': 'invalid', 'k1': 'c3RyaW5n'},
        {'uri': 'node_key@ip_address:port_number', 'callback': 'https://service.com/channel', 'k1': None},
    ])
    def skip__test_invalid_data(self, d):
        with pytest.raises(ValidationError):
            LnurlChannelResponse(**d)


class TestLnurlWithdrawResponse:

    @pytest.mark.parametrize('d', [
        {
            'callback': 'https://service.com/withdraw',
            'k1': 'c3RyaW5n',
            'min_withdrawable': 1000,
            'max_withdrawable': 2000,
        },
    ])
    def test_success_response(self, d):
        res = LnurlWithdrawResponse(**d)
        assert res.ok is True
        assert res.json() == (
            '{"tag": "withdrawRequest", "callback": "https://service.com/withdraw", "k1": "c3RyaW5n", '
            '"minWithdrawable": 1000, "maxWithdrawable": 2000, "defaultDescription": ""}'
        )
