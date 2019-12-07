import pytest

from lnurl.exceptions import InvalidLnurl, InvalidUrl
from lnurl.models.generics import HttpsUrl, Lnurl
from lnurl.utils import decode, encode


class TestUtils:
    valid_bc_address = 'BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4'

    @pytest.mark.parametrize('bech32,url', [
        ('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K'
         'XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU',
         'https://service.io/?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df')
    ])
    def test_decode(self, bech32, url):
        decoded_url = decode(bech32)
        assert isinstance(decoded_url, HttpsUrl) is True
        assert decoded_url == str(decoded_url) == url
        assert decoded_url.host == 'service.io'

    @pytest.mark.parametrize('bech32', [
        'abcdef1qpzry9x8gf2tvdw0s3jn54khce6mua7lmqqqxw',
        'split1checkupstagehandshakeupstreamerranterredcaperred2y9e3w',
        'BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4',
    ])
    def test_decode_nolnurl(self, bech32):
        with pytest.raises(InvalidLnurl):
            decode(bech32)

    @pytest.mark.parametrize('bech32,url', [
        ('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K'
         'XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU',
         'https://service.io/?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df')
    ])
    def test_encode(self, bech32, url):
        lnurl = encode(url)
        assert isinstance(lnurl, Lnurl) is True
        assert lnurl.bech32 == bech32
        assert lnurl.url.host == 'service.io'

    @pytest.mark.parametrize('url', [
        'http://service.io/'
    ])
    def test_encode_nohttps(self, url):
        with pytest.raises(InvalidUrl):
            encode(url)
