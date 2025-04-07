import json
from base64 import b64encode

import pytest

from lnurl import (
    AesAction,
    LnurlErrorResponse,
    LnurlPayActionResponse,
    LnurlPayResponse,
    LnurlPaySuccessAction,
    LnurlPaySuccessActions,
    LnurlResponse,
    LnurlSuccessResponse,
    LnurlWithdrawResponse,
)
from lnurl.exceptions import LnurlResponseException


class TestLnurlResponse:
    pay_res = json.loads(
        r'{"tag":"payRequest","metadata":"[[\"text/plain\",\"lorem ipsum blah blah\"]]",'
        '"callback":"https://lnurl.bigsun.xyz/lnurl-pay/callback/","maxSendable":300980,'
        '"minSendable":100980,"defaultDescription":"sample pay"}'
    )  # noqa
    pay_res_invalid = json.loads(r'{"tag":"payRequest","metadata":"[\"text\"\"plain\"]"}')
    withdraw_res = json.loads(
        '{"tag":"withdrawRequest","k1":"c67a8aa61f7c6cd457058916356ca80f5bfd00fa78ac2c1b3157391c2e9787de",'
        '"callback":"https://lnurl.bigsun.xyz/lnurl-withdraw/callback/?param1=1&param2=2",'
        '"maxWithdrawable":478980,"minWithdrawable":478980,"defaultDescription":"sample withdraw"}'
    )  # noqa
    pay_res_action_aes = {
        "pr": (
            "lnbc1pvjluezsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygspp5qqqsyqcyq5rqwzqfqqq"
            "syqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqdpl2pkx2ctnv5sxxmmwwd5kgetjypeh2ursdae8g6twvus8g6rfwvs8q"
            "un0dfjkxaq9qrsgq357wnc5r2ueh7ck6q93dj32dlqnls087fxdwk8qakdyafkq3yap9us6v52vjjsrvywa6rt52c"
            "m9r9zqt8r2t7mlcwspyetp5h2tztugp9lfyql"
        ),
        "routes": [],
        "successAction": {
            "tag": "aes",
            "description": "your will receive a secret message",
            "iv": b64encode(bytes(16)),
            "ciphertext": b64encode(bytes(32)),
        },
    }

    def test_error(self):
        res = LnurlResponse.from_dict({"status": "error", "reason": "error details..."})
        assert isinstance(res, LnurlErrorResponse)
        assert not res.ok
        assert res.error_msg == "error details..."

    def test_success(self):
        res = LnurlResponse.from_dict({"status": "OK"})
        assert isinstance(res, LnurlSuccessResponse)
        assert res.ok

    def test_unknown(self):
        with pytest.raises(LnurlResponseException):
            LnurlResponse.from_dict({"status": "unknown"})

    def test_pay(self):
        res = LnurlResponse.from_dict(self.pay_res)
        assert isinstance(res, LnurlPayResponse)
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

    # LUD-10
    def test_pay_action_aes(self):
        res = LnurlResponse.from_dict(self.pay_res_action_aes)
        assert isinstance(res, LnurlPayActionResponse)
        assert isinstance(res.success_action, AesAction)
        assert isinstance(res.success_action, LnurlPaySuccessAction)
        assert res.ok
        assert res.success_action
        assert res.success_action.tag == LnurlPaySuccessActions.aes
        assert res.success_action.description == "your will receive a secret message"
        assert len(res.success_action.iv) == 24
        assert len(res.success_action.ciphertext) == 44

    def test_withdraw(self):
        res = LnurlResponse.from_dict(self.withdraw_res)
        assert isinstance(res, LnurlWithdrawResponse)
        assert res.ok
        assert res.max_withdrawable == 478980
        assert res.max_sats == 478
        assert res.min_sats == 479
