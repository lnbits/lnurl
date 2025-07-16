from __future__ import annotations

import json
import os
import re
from enum import Enum
from hashlib import sha256
from typing import Generator, Optional
from urllib.parse import parse_qs

from pydantic import (
    AnyUrl,
    ConstrainedStr,
    Json,
    ValidationError,
    parse_obj_as,
    validator,
)
from pydantic.validators import str_validator

from .exceptions import InvalidLnurlPayMetadata, InvalidUrl, LnAddressError
from .helpers import _bech32_decode, _lnurl_clean, url_decode, url_encode


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

    def __init__(self, bech32: str, *, hrp: Optional[str] = None, data: Optional[list[int]] = None):
        str.__init__(bech32)
        self.hrp, self.data = (hrp, data) if hrp and data else self.__get_data__(bech32)

    @classmethod
    def __get_data__(cls, bech32: str) -> tuple[str, list[int]]:
        return _bech32_decode(bech32)

    @classmethod
    def __get_validators__(cls):
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> "Bech32":
        hrp, data = cls.__get_data__(value)
        return cls(value, hrp=hrp, data=data)


def ctrl_characters_validator(value: str) -> str:
    """Checks for control characters (unicode blocks C0 and C1, plus DEL)."""
    if re.compile(r"[\u0000-\u001f\u007f-\u009f]").search(value):
        raise InvalidUrl("URL contains control characters.")
    return value


def strict_rfc3986_validator(value: str) -> str:
    """Checks for RFC3986 compliance."""
    if os.environ.get("LNURL_STRICT_RFC3986", "0") == "1":
        if re.compile(r"[^]a-zA-Z0-9._~:/?#[@!$&'()*+,;=-]").search(value):
            raise InvalidUrl("URL is not RFC3986 compliant.")
    return value


def valid_lnurl_host(url: str) -> AnyUrl:
    """Validates the host part of a URL."""
    _url = parse_obj_as(AnyUrl, url)
    if not _url.host:
        raise InvalidUrl("URL host is required.")
    if _url.scheme == "http":
        if _url.host not in ["127.0.0.1", "0.0.0.0", "localhost"] and not _url.host.endswith(".onion"):
            raise InvalidUrl("HTTP scheme is only allowed for localhost or onion addresses.")
    return _url


class Url(AnyUrl):
    max_length = 2047  # https://stackoverflow.com/questions/417142/

    # LUD-17: Protocol schemes and raw (non bech32-encoded) URLs.
    allowed_schemes = {"https", "http", "lnurlc", "lnurlw", "lnurlp", "keyauth"}

    @property
    def is_lud17(self) -> bool:
        uris = ["lnurlc", "lnurlw", "lnurlp", "keyauth"]
        return any(self.scheme == uri for uri in uris)

    @classmethod
    def __get_validators__(cls) -> Generator:
        yield ctrl_characters_validator
        yield strict_rfc3986_validator
        yield valid_lnurl_host
        yield cls.validate

    @property
    def base(self) -> str:
        scheme = self.scheme
        if self.is_lud17:
            scheme = "https"
        hostport = f"{self.host}:{self.port}" if self.port else self.host
        return f"{scheme}://{hostport}{self.path or ''}"

    @property
    def query_params(self) -> dict:
        return {k: v[0] for k, v in parse_qs(self.query).items()}


class CallbackUrl(Url):
    """URL for callbacks. exclude lud17 schemes."""

    allowed_schemes = {"https", "http"}


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
    __slots__ = ("url", "bech32")

    def __new__(cls, lightning: str) -> Lnurl:
        url, bech32 = cls.clean(lightning)
        return str.__new__(cls, bech32 or url)

    def __init__(self, lightning: str):
        url, bech32 = self.clean(lightning)
        self.url = url
        self.bech32 = bech32
        return str.__init__(bech32 or url)

    @classmethod
    def __get_validators__(cls):
        yield str_validator
        yield cls.validate

    @classmethod
    def clean(cls, lightning: str) -> tuple[Url, Bech32 | None]:
        lightning = _lnurl_clean(lightning)
        if lightning.lower().startswith("lnurl1"):
            bech32 = parse_obj_as(Bech32, lightning)
            url = parse_obj_as(Url, url_decode(lightning))
        else:
            url = parse_obj_as(Url, lightning)
            if url.is_lud17:
                # LUD-17: Protocol schemes and raw (non bech32-encoded) URLs.
                # no bech32 encoding for lud17
                bech32 = None
            else:
                bech32 = parse_obj_as(Bech32, url_encode(url))
        return url, bech32

    @classmethod
    def validate(cls, lightning: str) -> Lnurl:
        _ = cls.clean(lightning)
        return cls(lightning)

    @property
    def callback_url(self) -> CallbackUrl:
        return parse_obj_as(CallbackUrl, self.url.base)

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

    # LUD-17: Protocol schemes and raw (non bech32-encoded) URLs.
    @property
    def is_lud17(self) -> bool:
        return self.url.is_lud17


class LnAddress(ReprMixin, str):
    """Lightning address of form `user+tag@host`"""

    slots = ("address", "url", "tag")

    def __new__(cls, address: str) -> LnAddress:
        return str.__new__(cls, address)

    def __init__(self, address: str):
        str.__init__(address)
        if not self.is_valid_lnaddress(address):
            raise LnAddressError("Invalid Lightning address.")
        self.url = self.__get_url__(address)
        if "+" in address:
            self.tag: Optional[str] = address.split("+", 1)[1].split("@", 1)[0]
            self.address = address.replace(f"+{self.tag}", "", 1)
        else:
            self.tag = None
            self.address = address

    # LUD-16: Paying to static internet identifiers.
    @validator("address")
    def is_valid_lnaddress(cls, address: str) -> bool:
        # A user can then type these on a WALLET. The <username> is limited
        # to a-z-1-9-_.. Please note that this is way more strict than common
        # email addresses as it allows fewer symbols and only lowercase characters.
        lnaddress_regex = r"[a-z0-9\._%+-]+@[A-Za-z0-9\.-]+\.[A-Za-z]{2,63}"
        return re.fullmatch(lnaddress_regex, address) is not None

    @classmethod
    def __get_url__(cls, address: str) -> CallbackUrl:
        name, domain = address.split("@")
        url = ("http://" if domain.endswith(".onion") else "https://") + domain + "/.well-known/lnurlp/" + name
        return parse_obj_as(CallbackUrl, url)


class LnurlPayMetadata(ReprMixin, str):
    # LUD-16: Paying to static internet identifiers. "text/identifier", "text/email", "text/tag"
    # LUD-20: Long payment description for pay protocol. "text/long-desc"
    valid_metadata_mime_types = {
        "text/plain",
        "image/png;base64",
        "image/jpeg;base64",
        "text/identifier",
        "text/email",
        "text/tag",
        "text/long-desc",
    }

    __slots__ = ("_list",)

    def __new__(cls, json_str: str, **_) -> LnurlPayMetadata:
        return str.__new__(cls, json_str)

    def __init__(self, json_str: str, *, json_obj: Optional[list] = None):
        str.__init__(json_str)
        self._list = json_obj if json_obj else self.__validate_metadata__(json_str)

    @classmethod
    def __validate_metadata__(cls, json_str: str) -> list[tuple[str, str]]:
        try:
            parse_obj_as(Json[list[tuple[str, str]]], json_str)
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
    def images(self) -> list[tuple[str, str]]:
        return [x for x in self._list if x[0].startswith("image/")]

    def list(self) -> list[tuple[str, str]]:
        return self._list


class InitializationVectorBase64(ConstrainedStr):
    min_length = 24
    max_length = 24


class CiphertextBase64(ConstrainedStr):
    min_length = 24
    max_length = 4096


class Max144Str(ConstrainedStr):
    max_length = 144


# LUD-04: auth base spec.
class LnurlAuthActions(Enum):
    """Enum for auth actions"""

    login = "login"
    register = "register"
    link = "link"
    auth = "auth"


class LnurlPaySuccessActionTag(Enum):
    """Enum for success action tags"""

    aes = "aes"
    message = "message"
    url = "url"


class LnurlStatus(Enum):
    """Enum for status"""

    ok = "OK"
    error = "ERROR"


class LnurlResponseTag(Enum):
    """Enum for response tags"""

    login = "login"
    channelRequest = "channelRequest"
    hostedChannelRequest = "hostedChannelRequest"
    payRequest = "payRequest"
    withdrawRequest = "withdrawRequest"
