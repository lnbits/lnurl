import pytest

from lnurl.exceptions import InvalidLnurl, InvalidScheme, InvalidUrl
from lnurl.utils import decode, encode, validate_url


class TestUtils:
    lnurl = (
        'https://service.ln/?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df',
        'LNURL1DP68GURN8GHJ7UM9WFMXJCM99EKXUTELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K'
        'XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCSRL7N6'
    )
    valid_bc_address = 'BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4'

    def test_decode(self):
        assert decode(self.lnurl[1]) == self.lnurl[0]

        # only LNURLs can be decoded
        with pytest.raises(InvalidLnurl):
            decode(self.valid_bc_address)

    def test_encode(self):
        assert encode(self.lnurl[0]) == self.lnurl[1]

        # https is enforced by default
        with pytest.raises(InvalidScheme):
            encode('http://lndhub.io/')
