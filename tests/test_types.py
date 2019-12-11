import pytest

from pydantic import ValidationError, parse_obj_as

from lnurl.functions import _lnurl_clean
from lnurl.types import HttpsUrl, LightningInvoice, LightningNodeUri, Lnurl


class TestHttpsUrl:

    def test_valid(self):
        url = parse_obj_as(HttpsUrl, 'https://service.io/?q=3fc3645b439ce8e7&test=ok')
        assert url.host == 'service.io'
        assert url.base == 'https://service.io/'
        assert url.query_params == {'q': '3fc3645b439ce8e7', 'test': 'ok'}

    @pytest.mark.parametrize('url', [
        f'https://service.io/?hash={"x" * 4096}',
        'http://📙.la/⚡',  # https://emojipedia.org/high-voltage-sign/
        'http://xn--yt8h.la/%E2%9A%A1',
    ])
    def test_invalid_data(self, url):
        with pytest.raises(ValidationError):
            parse_obj_as(HttpsUrl, url)


class TestLightningInvoice:

    @pytest.mark.xfail(raises=NotImplementedError)
    @pytest.mark.parametrize('bech32,hrp,prefix,amount,h', [
        ('lntb20m1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqhp58yjmdan79s6qqdhdzgynm4zwqd'
         '5d7xmw5fk98klysy043l2ahrqsfpp3x9et2e20v6pu37c5d9vax37wxq72un98k6vcx9fz94w0qf237cm2rqv9pmn5lnexfvf55'
         '79slr4zq3u8kmczecytdx0xg9rwzngp7e6guwqpqlhssu04sucpnz4axcv2dstmknqq6jsk2l', 'lntb20m', 'lntb', 20,
         'h'),
    ])
    def test_valid(self, bech32, hrp, prefix, amount, h):
        invoice = LightningInvoice(bech32)
        assert invoice == parse_obj_as(LightningInvoice, bech32)
        assert invoice.hrp == hrp
        assert invoice.prefix == prefix
        assert invoice.amount == amount
        assert invoice.h == h


class TestLightningNode:

    def test_valid(self):
        node = parse_obj_as(LightningNodeUri, 'node_key@ip_address:port_number')
        assert node.key == 'node_key'
        assert node.ip == 'ip_address'
        assert node.port == 'port_number'

    @pytest.mark.parametrize('uri', [
        'https://service.io/node',
        'node_key@ip_address',
        'ip_address:port_number',
    ])
    def test_invalid_data(self, uri):
        with pytest.raises(ValidationError):
            parse_obj_as(LightningNodeUri, uri)


class TestLnurl:

    @pytest.mark.parametrize('lightning,url', [
        ('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K'
         'XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU',
         'https://service.io/?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df'),
        ('lightning:LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWE3JX56NXCFK89JN2V3K'
         'XUCRSVTY8YMXGCMYXV6RQD3EXDSKVCTZV5CRGCN9XA3RQCMRVSCNWWRYVCYAE0UU',
         'https://service.io/?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df')
    ])
    def test_valid(self, lightning, url):
        lnurl = Lnurl(lightning)
        assert lnurl == lnurl.bech32 == _lnurl_clean(lightning) == parse_obj_as(Lnurl, lightning)
        assert lnurl.bech32.hrp == 'lnurl'
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
            parse_obj_as(Lnurl, bech32)
