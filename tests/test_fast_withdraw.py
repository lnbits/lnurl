import pytest
from pydantic import parse_obj_as

from lnurl import encode
from lnurl.models import LnurlWithdrawResponse

url = "https://lnbits.com/withdraw/api/v1/lnurl"
url2 = f"{url}?tag=withdrawRequest"
url3 = f"{url2}&k1={16  * '0'}"
url4 = f"{url3}&callback={url}&defaultDescription=default"
url5 = f"{url4}&minWithdrawable=1000&maxWithdrawable=1000000"


class TestFastWithdraw:
    @pytest.mark.parametrize(
        "url, expected",
        [
            (url, False),
            (url2, False),
            (url3, False),
            (url4, False),
            (url5, True),
        ],
    )
    def test_is_lnurl_fast_withdraw(self, url: str, expected: bool):
        lnurl = encode(url)
        assert lnurl.is_fast_withdraw == expected

    def test_set_lnurl_fast_withdraw(self):
        response = parse_obj_as(
            LnurlWithdrawResponse,
            {
                "tag": "withdrawRequest",
                "k1": "0" * 16,
                "minWithdrawable": 1000,
                "maxWithdrawable": 1000000,
                "defaultDescription": "default",
                "callback": url,
            },
        )
        lnurl = encode(f"{url}?{response.fast_withdraw_query}")
        assert lnurl.is_fast_withdraw is True
