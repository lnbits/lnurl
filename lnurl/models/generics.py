from bech32 import bech32_decode
from pydantic import BaseModel, HttpUrl, PositiveInt
from pydantic.validators import str_validator
from urllib.parse import urlparse, parse_qs
from typing import Any, Optional, Set

from lnurl.tools import _bech32_decode, _lnurl_decode


class ReprMixin:

    def __repr__(self) -> str:
        extra = ', '.join(f'{n}={getattr(self, n)!r}' for n in self.__slots__ if getattr(self, n) is not None)
        return f'{self.__class__.__name__}({super().__repr__()}, {extra})'


class Bech32(str, ReprMixin):
    """Bech32: checksummed base32."""
    allowed_hrp: Optional[Set[str]] = None

    __slots__ = ('hrp', 'data')

    def __new__(cls, bech32: str, **kwargs) -> object:
        return str.__new__(cls, bech32)

    def __init__(self, bech32: str, *, hrp: Optional[str] = None, data: Optional[Any] = None):
        str.__init__(bech32)
        self.hrp = hrp
        self.data = data

    def __repr__(self) -> str:
        extra = ', '.join(f'{n}={getattr(self, n)!r}' for n in self.__slots__ if getattr(self, n) is not None)
        return f'{self.__class__.__name__}({super().__repr__()}, {extra})'

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> 'Bech32':
        hrp, data = _bech32_decode(value, allowed_hrp=cls.allowed_hrp)
        return cls(value, hrp=hrp, data=data)

    @property
    def h(self):
        raise NotImplementedError


class HttpsUrl(HttpUrl):
    """HTTPS URL."""
    allowed_schemes = {'https'}
    max_length = 2047  # https://stackoverflow.com/questions/417142/

    @property
    def base(self) -> str:
        return f'{self.scheme}://{self.host}{self.path}'

    @property
    def query_params(self) -> dict:
        return {k: v[0] for k, v in parse_qs(self.query).items()}


class LightningInvoiceBech32(Bech32):
    """Lightning invoice."""
    allowed_hrp = {'lnbc'}


class LightningNodeUri(str, ReprMixin):
    """Remote node address of form `node_key@ip_address:port_number`."""

    __slots__ = ('key', 'ip', 'port')

    def __new__(cls, uri: str, **kwargs) -> object:
        return str.__new__(cls, uri)

    def __init__(self, uri: str, *, key: Optional[str] = None, ip: Optional[str] = None, port: Optional[str] = None):
        str.__init__(uri)
        self.key = key
        self.ip = ip
        self.port = port

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> 'LightningNodeUri':
        try:
            key, netloc = value.split('@')
            ip, port = netloc.split(':')
        except Exception:
            raise ValueError

        return cls(value, key=key, ip=ip, port=port)


class Lnurl(str, ReprMixin):
    __slots__ = ('bech32', 'url')

    def __new__(cls, bech32: str, **kwargs) -> object:
        return str.__new__(cls, bech32)

    def __init__(self, bech32: str, *, url: Optional[HttpsUrl] = None):
        str.__init__(bech32)
        self.bech32 = bech32
        self.url = url

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> 'Lnurl':
        class HttpsUrlModel(BaseModel):
            url: HttpsUrl

        url = HttpsUrlModel(url=_lnurl_decode(value)).url
        return cls(value, url=url)

    @property
    def is_login(self) -> bool:
        return 'tag' in self.url.query_params and self.url.query_params['tag'] == 'login'


class Millisatoshi(PositiveInt):
    """A thousandth of a satoshi."""
