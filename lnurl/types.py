from __future__ import annotations

import json
import os
import re
from hashlib import sha256
from typing import List, Optional, Tuple, Union
from urllib.parse import parse_qs

from pydantic import (
    ConstrainedStr,
    HttpUrl,
    Json,
    ValidationError,
    parse_obj_as,
    validator,
)
from pydantic.errors import UrlHostTldError, UrlSchemeError
from pydantic.networks import Parts
from pydantic.validators import str_validator

from .exceptions import InvalidLnurlPayMetadata
from .helpers import _bech32_decode, _lnurl_clean, url_decode


def ctrl_characters_validator(value: str) -> str:
    """Checks for control characters (unicode blocks C0 and C1, plus DEL)."""
    if re.compile(r"[\u0000-\u001f\u007f-\u009f]").search(value):
        raise ValueError
    return value


def strict_rfc3986_validator(value: str) -> str:
    """Checks for RFC3986 compliance."""
    if re.compile(r"[^]a-zA-Z0-9._~:/?#[@!$&'()*+,;=-]").search(value):
        raise ValueError
    return value


class ReprMixin:
    def __repr__(self) -> str:
        attrs = [  # type: ignore
            outer_slot  # type: ignore
            for outer_slot in [slot for slot in self.__slots__ if not slot.startswith("_")]  # type: ignore
            if getattr(self, outer_slot)  # type: ignore
        ]  # type: ignore
        extra = ", " + ", ".join(f"{n}={getattr(self, n).__repr__()}" for n in attrs) if attrs else ""
        return f"{self.__class__.__name__}({super().__repr__()}{extra})"


class Bech32(ReprMixin, str):
    """Bech32 string."""

    __slots__ = ("hrp", "data")

    def __new__(cls, bech32: str, **_) -> "Bech32":
        return str.__new__(cls, bech32)

    def __init__(self, bech32: str, *, hrp: Optional[str] = None, data: Optional[List[int]] = None):
        str.__init__(bech32)
        self.hrp, self.data = (hrp, data) if hrp and data else self.__get_data__(bech32)

    @classmethod
    def __get_data__(cls, bech32: str) -> Tuple[str, List[int]]:
        return _bech32_decode(bech32)

    @classmethod
    def __get_validators__(cls):
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> "Bech32":
        hrp, data = cls.__get_data__(value)
        return cls(value, hrp=hrp, data=data)


class Url(HttpUrl):
    """URL with extra validations over pydantic's `HttpUrl`."""

    max_length = 2047  # https://stackoverflow.com/questions/417142/

    @classmethod
    def __get_validators__(cls):
        yield ctrl_characters_validator
        if os.environ.get("LNURL_STRICT_RFC3986", "0") == "1":
            yield strict_rfc3986_validator
        yield cls.validate

    @property
    def base(self) -> str:
        hostport = f"{self.host}:{self.port}" if self.port else self.host
        return f"{self.scheme}://{hostport}{self.path}"

    @property
    def query_params(self) -> dict:
        return {k: v[0] for k, v in parse_qs(self.query).items()}


class DebugUrl(Url):
    """Unsecure web URL, to make developers life easier."""

    allowed_schemes = {"http"}

    @classmethod
    def validate_host(cls, parts: Parts) -> Tuple[str, Optional[str], str, bool]:
        host, tld, host_type, rebuild = super().validate_host(parts)
        if host not in ["127.0.0.1", "0.0.0.0"]:
            raise UrlSchemeError()
        return host, tld, host_type, rebuild


class ClearnetUrl(Url):
    """Secure web URL."""

    allowed_schemes = {"https"}


class OnionUrl(Url):
    """Tor anonymous onion service."""

    allowed_schemes = {"https", "http"}

    @classmethod
    def validate_host(cls, parts: Parts) -> Tuple[str, Optional[str], str, bool]:
        host, tld, host_type, rebuild = super().validate_host(parts)
        if tld != "onion":
            raise UrlHostTldError()
        return host, tld, host_type, rebuild


class LightningInvoice(Bech32):
    """Bech32 Lightning invoice."""


class LightningNodeUri(ReprMixin, str):
    """Remote node address of form `node_key@ip_address:port_number`."""

    __slots__ = ("key", "ip", "port")

    def __new__(cls, uri: str, **_) -> "LightningNodeUri":
        return str.__new__(cls, uri)

    def __init__(self, uri: str, *, key: Optional[str] = None, ip: Optional[str] = None, port: Optional[str] = None):
        str.__init__(uri)
        self.key = key
        self.ip = ip
        self.port = port

    @classmethod
    def __get_validators__(cls):
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> "LightningNodeUri":
        try:
            key, netloc = value.split("@")
            ip, port = netloc.split(":")
        except Exception:
            raise ValueError

        return cls(value, key=key, ip=ip, port=port)


class Lnurl(ReprMixin, str):
    __slots__ = ("bech32", "url")

    def __new__(cls, lightning: str, **_) -> Lnurl:
        return str.__new__(cls, _lnurl_clean(lightning))

    def __init__(self, lightning: str, *, url: Optional[Union[OnionUrl, ClearnetUrl, DebugUrl]] = None):
        bech32 = _lnurl_clean(lightning)
        str.__init__(bech32)
        self.bech32 = Bech32(bech32)
        self.url = url if url else self.__get_url__(bech32)

    @classmethod
    def __get_url__(cls, bech32: str) -> Union[OnionUrl, ClearnetUrl, DebugUrl]:
        url: str = url_decode(bech32)
        return parse_obj_as(Union[OnionUrl, ClearnetUrl, DebugUrl], url)  # type: ignore

    @classmethod
    def __get_validators__(cls):
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> Lnurl:
        return cls(value, url=cls.__get_url__(value))

    # LUD-04: auth base spec.
    @property
    def is_login(self) -> bool:
        return self.url.query_params.get("tag") == "login"

    # LUD-08: Fast withdrawRequest.
    @property
    def is_fast_withdraw(self) -> bool:
        q = self.url.query_params
        return (
            q.get("tag") == "withdrawRequest"
            and q.get("k1") is not None
            and q.get("minWithdrawable") is not None
            and q.get("maxWithdrawable") is not None
            and q.get("defaultDescription") is not None
            and q.get("callback") is not None
        )


class LnAddress(ReprMixin, str):
    """Lightning address of form `user@host`"""

    slots = ("address", "url")

    def __new__(cls, address: str, **_) -> LnAddress:
        return str.__new__(cls, address)

    def __init__(self, address: str):
        str.__init__(address)
        if not self.is_valid_lnaddress(address):
            raise ValueError("Invalid Lightning address.")
        self.address = address
        self.url = self.__get_url__(address)

    # LUD-16: Paying to static internet identifiers.
    @validator("address")
    def is_valid_lnaddress(cls, address: str) -> bool:
        # A user can then type these on a WALLET. The <username> is limited
        # to a-z-1-9-_.. Please note that this is way more strict than common
        # email addresses as it allows fewer symbols and only lowercase characters.
        lnaddress_regex = r"[a-z0-9\._%+-]+@[A-Za-z0-9\.-]+\.[A-Za-z]{2,63}"
        return re.fullmatch(lnaddress_regex, address) is not None

    @classmethod
    def __get_url__(cls, address: str) -> Union[OnionUrl, ClearnetUrl, DebugUrl]:
        name, domain = address.split("@")
        url = ("http://" if domain.endswith(".onion") else "https://") + domain + "/.well-known/lnurlp/" + name
        return parse_obj_as(Union[OnionUrl, ClearnetUrl, DebugUrl], url)  # type: ignore


class LnurlPayMetadata(ReprMixin, str):
    # LUD-16: Paying to static internet identifiers. "text/identifier", "text/email"
    # LUD-20: Long payment description for pay protocol. "text/long-desc"
    valid_metadata_mime_types = {
        "text/plain",
        "image/png;base64",
        "image/jpeg;base64",
        "text/identifier",
        "text/email",
        "text/long-desc",
    }

    __slots__ = ("_list",)

    def __new__(cls, json_str: str, **_) -> LnurlPayMetadata:
        return str.__new__(cls, json_str)

    def __init__(self, json_str: str, *, json_obj: Optional[List] = None):
        str.__init__(json_str)
        self._list = json_obj if json_obj else self.__validate_metadata__(json_str)

    @classmethod
    def __validate_metadata__(cls, json_str: str) -> List[Tuple[str, str]]:
        try:
            parse_obj_as(Json[List[Tuple[str, str]]], json_str)
            data = [(str(item[0]), str(item[1])) for item in json.loads(json_str)]
        except ValidationError:
            raise InvalidLnurlPayMetadata

        clean_data = [x for x in data if x[0] in cls.valid_metadata_mime_types]
        mime_types = [x[0] for x in clean_data]
        counts = {x: mime_types.count(x) for x in mime_types}

        if (
            not clean_data
            or ("text/plain" not in mime_types and "text/long-desc" not in mime_types)
            or counts["text/plain"] > 1
        ):
            raise InvalidLnurlPayMetadata

        return clean_data

    @classmethod
    def __get_validators__(cls):
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> LnurlPayMetadata:
        return cls(value, json_obj=cls.__validate_metadata__(value))

    @property
    def h(self) -> str:
        return sha256(self.encode("utf-8")).hexdigest()

    @property
    def text(self) -> str:
        output = ""

        for metadata in self._list:
            if metadata[0] == "text/plain":
                output = metadata[1]
                break

        return output

    @property
    def images(self) -> List[Tuple[str, str]]:
        return [x for x in self._list if x[0].startswith("image/")]

    def list(self) -> List[Tuple[str, str]]:
        return self._list


class InitializationVectorBase64(ConstrainedStr):
    min_length = 24
    max_length = 24


class CiphertextBase64(ConstrainedStr):
    min_length = 24
    max_length = 4096


class Max144Str(ConstrainedStr):
    max_length = 144
