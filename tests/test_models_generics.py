import pytest

from pydantic import BaseModel, ValidationError

from lnurl.models.generics import HttpsUrl, LightningNodeUri


class HttpsUrlModel(BaseModel):
    url: HttpsUrl


class TestHttpsUrl:

    def test_valid(self):
        url = HttpsUrlModel(url='https://service.io/?q=3fc3645b439ce8e7&test=ok').url
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
            HttpsUrlModel(url=url)


class LightningNodeUriModel(BaseModel):
    uri: LightningNodeUri


class TestLightningNode:

    def test_valid(self):
        node = LightningNodeUriModel(uri='node_key@ip_address:port_number').uri
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
            LightningNodeUriModel(uri=uri)
