import pytest

from pydantic import BaseModel, ValidationError

from lnurl.models.generics import Lnurl


class LnurlModel(BaseModel):
    lnurl: Lnurl


class TestLnurl:

    @pytest.mark.parametrize('bech32,url', [
        ('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K'
         'XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU',
         'https://service.io/?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df'),
        ('lightning:LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K'
         'XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU',
         'https://service.io/?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df')
    ])
    def test_valid(self, bech32, url):
        lnurl = LnurlModel(lnurl=bech32).lnurl
        assert lnurl == lnurl.bech32 == bech32
        assert lnurl.url == url
        assert lnurl.url.base == 'https://service.io/'
        assert lnurl.url.query_params == {'q': '3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df'}
        assert lnurl.is_login is False

    @pytest.mark.parametrize('bech32', [
        'abcdef1qpzry9x8gf2tvdw0s3jn54khce6mua7lmqqqxw',
        'split1checkupstagehandshakeupstreamerranterredcaperred2y9e3w',
        'BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4',
    ])
    def test_decode_nolnurl(self, bech32):
        with pytest.raises(ValidationError):
            LnurlModel(lnurl=bech32)
