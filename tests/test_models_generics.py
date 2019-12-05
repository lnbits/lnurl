import pytest

from pydantic import BaseModel, ValidationError

from lnurl.models.generics import HttpsUrl, LightningNodeUri, Lnurl


class HttpsUrlModel(BaseModel):
    url: HttpsUrl


class TestHttpsUrl:

    def test_valid(self):
        m = HttpsUrlModel(url='https://service.com/api?q=3fc3645b439ce8e7&test=ok')
        assert m.url.host == 'service.com'
        assert m.url.base == 'https://service.com/api'
        assert m.url.query_params == {'q': '3fc3645b439ce8e7', 'test': 'ok'}

    @pytest.mark.parametrize('url', [
        f'https://service.com/?hash={"x" * 4096}',
        'http://📙.la/⚡',  # https://emojipedia.org/high-voltage-sign/
        'http://xn--yt8h.la/%E2%9A%A1',
    ])
    def test_invalid_data(self, url):
        with pytest.raises(ValidationError):
            HttpsUrlModel(url=url)


class LightningNodeUriModel(BaseModel):
    uri: LightningNodeUri


class TestLightningNode:

    def skip__test_valid(self):
        m = LightningNodeUriModel(uri='node_key@ip_address:port_number')
        assert m.uri.host == 'ip_address'
        assert m.uri.port == 'port_number'


class LnurlModel(BaseModel):
    lnurl: Lnurl


class TestLnurl:

    @pytest.mark.parametrize('lnurl,url', [
        ('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E3K7MF0V9CXJ0M385EKVCENXC6R2C35XVUKXEFCV5MKVV34X'
         '5EKZD3EV56NYD3HXQURZEPEXEJXXEPNXSCRVWFNV9NXZCN9XQ6XYEFHVGCXXCMYXYMNSERXFQ5FNS',
         'https://service.com/api?q=3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df')
    ])
    def skip__test_valid(self, lnurl, url):
        ln = LnurlModel(lnurl=lnurl)
        assert ln.lnurl.bech32 == lnurl
        assert ln.lnurl.url == url
        assert ln.lnurl.url.base == 'https://service.com/api'
        assert ln.lnurl.url.query_params == {'q': '3fc3645b439ce8e7f2553a69e5267081d96dcd340693afabe04be7b0ccd178df'}
