from bech32 import bech32_decode
from pydantic import BaseModel, AnyUrl, HttpUrl, PositiveInt
from urllib.parse import parse_qs

from lnurl.exceptions import LnurlResponseException, InvalidLnurlTag, InvalidLnurlPayMetadata
from lnurl.utils import decode


class Bech32Invoice(str):

    def __init__(self, bech32):
        str.__init__(bech32)
        self.hrp, self.data = bech32_decode(self)

    @property
    def h(self):
        raise NotImplementedError


class HttpsUrl(HttpUrl):
    """HTTPS URL."""
    allowed_schemes = {'https'}

    @property
    def base(self) -> str:
        return f'{self.scheme}://{self.host}{self.path}'

    @property
    def query_params(self) -> dict:
        return {k: v[0] for k, v in parse_qs(self.query).items()}


class MilliSatoshi(PositiveInt):
    pass


class LightningNodeUri(AnyUrl):
    """Remote node address of form `node_key@ip_address:port_number`."""
    scheme: str = ''
    user_required = True


class Lnurl(BaseModel):
    __root__: str

    @property
    def bech32(self) -> str:
        return self
