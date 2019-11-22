import json
import pytest

from lnurl.exceptions import InvalidLnurlTag, InvalidLnurlPayMetadata
from lnurl.models import Lnurl, LnurlPayResponse, LnurlWithdrawResponse


class TestLnurl:
    lnurl = (
        'https://service.com/api?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df',
        'LNURL1DP68GURN8GHJ7UM9WFMXJCM99E3K7MF0V9CXJ0M385EKVCENXC6R2C35XVUKXEFCV5MKVV34X'
        '5EKZD3EV56NYD3HXQURZEPEXEJXXEPNXSCRVWFNV9NXZCN9XQ6XYEFHVGCXXCMYXYMNSERXFQ5FNS'
    )

    def test_properties(self):
        lnurl = Lnurl(self.lnurl[1])
        assert lnurl.bech32 == self.lnurl[1]
        assert lnurl.url.full == lnurl.decoded == self.lnurl[0]
        assert lnurl.url.base == 'https://service.com/api'
        assert lnurl.url.query_params == {
            'q': '3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df',
        }


class TestLnurlResponse:
    error_res = json.loads('{"status":"ERROR","reason":"error details..."}')
    pay_res = json.loads(r'{"status":"OK","tag":"payRequest","metadata":"[[\"text/plain\",\"lorem ipsum blah blah\"]]","k1":"c67a8aa61f7c6cd457058916356ca80f5bfd00fa78ac2c1b3157391c2e9787de","callback":"https://lnurl.bigsun.xyz/lnurl-pay/callback/","maxSendable":300980,"minSendable":100980,"defaultDescription":"sample pay"}')  # noqa
    pay_res_invalid = json.loads(r'{"status":"OK","tag":"payRequest","metadata":"[\"text\"\"plain\"]"}')
    withdraw_res = json.loads('{"status":"OK","tag":"withdrawRequest","k1":"c67a8aa61f7c6cd457058916356ca80f5bfd00fa78ac2c1b3157391c2e9787de","callback":"https://lnurl.bigsun.xyz/lnurl-withdraw/callback/?param1=1&param2=2","maxWithdrawable":478980,"minWithdrawable":478980,"defaultDescription":"sample withdraw"}')  # noqa

    def test_invalid_response(self):
        with pytest.raises(InvalidLnurlTag):
            LnurlPayResponse(self.withdraw_res)

    def test_error(self):
        res = LnurlPayResponse(self.error_res)
        assert res.ok is False
        assert res.error_msg == 'error details...'

    def test_pay(self):
        res = LnurlPayResponse(self.pay_res)
        assert res.ok is True
        assert res.max_sats == 300
        assert res.min_sats == 101
        assert res.metadata == [('text/plain', 'lorem ipsum blah blah')]

    def test_pay_invalid_metadata(self):
        with pytest.raises(InvalidLnurlPayMetadata):
            LnurlPayResponse(self.pay_res_invalid)

    def test_withdraw(self):
        res = LnurlWithdrawResponse(self.withdraw_res)
        assert res.ok is True
        assert res.max_sats == 478
        assert res.min_sats == 479
