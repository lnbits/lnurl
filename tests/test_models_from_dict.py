import json
import pytest

from lnurl import LnurlResponse
from lnurl.exceptions import LnurlResponseException


class TestLnurlResponse:
    pay_res = json.loads(
        r'{"tag":"payRequest","metadata":"[[\"text/plain\",\"lorem ipsum blah blah\"]]","k1":"c67a8aa61f7c6cd457058916356ca80f5bfd00fa78ac2c1b3157391c2e9787de","callback":"https://lnurl.bigsun.xyz/lnurl-pay/callback/","maxSendable":300980,"minSendable":100980,"defaultDescription":"sample pay"}'
    )  # noqa
    pay_res_invalid = json.loads(r'{"tag":"payRequest","metadata":"[\"text\"\"plain\"]"}')
    withdraw_res = json.loads(
        '{"tag":"withdrawRequest","k1":"c67a8aa61f7c6cd457058916356ca80f5bfd00fa78ac2c1b3157391c2e9787de","callback":"https://lnurl.bigsun.xyz/lnurl-withdraw/callback/?param1=1&param2=2","maxWithdrawable":478980,"minWithdrawable":478980,"defaultDescription":"sample withdraw"}'
    )  # noqa

    def test_error(self):
        res = LnurlResponse.from_dict({"status": "error", "reason": "error details..."})
        assert not res.ok
        assert res.error_msg == "error details..."

    def test_success(self):
        res = LnurlResponse.from_dict({"status": "OK"})
        assert res.ok

    def test_unknown(self):
        with pytest.raises(LnurlResponseException):
            LnurlResponse.from_dict({"status": "unknown"})

    def test_pay(self):
        res = LnurlResponse.from_dict(self.pay_res)
        assert res.ok
        assert res.max_sats == 300
        assert res.min_sats == 101
        assert res.metadata == '[["text/plain","lorem ipsum blah blah"]]'
        assert res.metadata.list() == [("text/plain", "lorem ipsum blah blah")]
        assert not res.metadata.images
        assert res.metadata.text == "lorem ipsum blah blah"
        assert res.metadata.h == "d824d0ea606c5a9665279c31cf185528a8df2875ea93f1f75e501e354b33e90a"

    def test_pay_invalid_metadata(self):
        with pytest.raises(LnurlResponseException):
            LnurlResponse.from_dict(self.pay_res_invalid)

    def test_withdraw(self):
        res = LnurlResponse.from_dict(self.withdraw_res)
        assert res.ok
        assert res.max_withdrawable == 478980
        assert res.max_sats == 478
        assert res.min_sats == 479
