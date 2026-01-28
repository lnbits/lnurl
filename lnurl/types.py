from __future__ import annotations

import json
import os
import re
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import Annotated, Any, Optional

from pydantic import (
    AfterValidator,
    AnyUrl,
    BeforeValidator,
    GetCoreSchemaHandler,
    HttpUrl,
    Json,
    StringConstraints,
    TypeAdapter,
    UrlConstraints,
    ValidationError,
)
from pydantic_core import core_schema

from .exceptions import InvalidLnurlPayMetadata, InvalidUrl, LnAddressError
from .helpers import _bech32_decode, _lnurl_clean, url_decode, url_encode

INSECURE_HOSTS = ["127.0.0.1", "0.0.0.0", "localhost"]
LUD17_SCHEMES = ["lnurlc", "lnurlw", "lnurlp", "keyauth"]


class Bech32(str):
    """Bech32 string."""

    __slots__ = ("hrp", "data")

    def __new__(cls, bech32: str, **_) -> "Bech32":
        return str.__new__(cls, bech32)

    def __init__(self, bech32: str, hrp: Optional[str] = None, data: Optional[list[int]] = None):
        str.__init__(bech32)
        self.hrp, self.data = (hrp, data) if hrp and data else self.__get_data__(bech32)

    @classmethod
    def __get_data__(cls, bech32: str) -> tuple[str, list[int]]:
        return _bech32_decode(bech32)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:

        def validate(value: Any):
            hrp, data = cls.__get_data__(str(value))
            value = cls(str(value), hrp=hrp, data=data)
            return value

        def serialize(value: Any) -> str:
            return str(value)

        return core_schema.no_info_after_validator_function(
            validate,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(cls),
                    core_schema.str_schema(),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(serialize, when_used="json"),
        )


def ctrl_characters_validator(value: AnyUrl) -> AnyUrl:
    """Checks for control characters (unicode blocks C0 and C1, plus DEL)."""
    if re.compile(r"[\u0000-\u001f\u007f-\u009f]").search(str(value)):
        raise InvalidUrl("URL contains control characters.")
    return value


def strict_rfc3986_validator(value: AnyUrl) -> AnyUrl:
    """Checks for RFC3986 compliance."""
    if os.environ.get("LNURL_STRICT_RFC3986", "0") == "1":
        if re.compile(r"[^]a-zA-Z0-9._~:/?#[@!$&'()*+,;=-]").search(str(value)):
            raise InvalidUrl("URL is not RFC3986 compliant.")
    return value


def validate_http_host(url: AnyUrl) -> AnyUrl:
    """Ensure only localhost or .onion addresses can use http://"""
    if not url.host:
        raise InvalidUrl("URL must have a valid host.")
    if not url.scheme == "http" or url.host.endswith(".onion"):
        return url
    if url.host not in INSECURE_HOSTS:
        raise InvalidUrl("HTTP scheme is only allowed for localhost or onion addresses.")
    return url


Url = Annotated[
    AnyUrl,
    UrlConstraints(
        max_length=2047,  # https://stackoverflow.com/questions/417142/
        allowed_schemes=[  # LUD-17: Protocol schemes and raw (non bech32-encoded) URLs.
            "https",
            "http",
            "lnurlc",
            "lnurlw",
            "lnurlp",
            "keyauth",
        ],
    ),
    BeforeValidator(ctrl_characters_validator),
    BeforeValidator(strict_rfc3986_validator),
    AfterValidator(validate_http_host),
]

# URL for callbacks. exclude lud17 schemes.
CallbackUrl = Annotated[
    HttpUrl,
    BeforeValidator(ctrl_characters_validator),
    BeforeValidator(strict_rfc3986_validator),
    AfterValidator(validate_http_host),
]

# class Url(AnyUrl):
#     max_length = 2047  # https://stackoverflow.com/questions/417142/

#     # LUD-17: Protocol schemes and raw (non bech32-encoded) URLs.
#     allowed_schemes = {"https", "http", "lnurlc", "lnurlw", "lnurlp", "keyauth"}

#     @property
#     def is_lud17(self) -> bool:
#         uris = ["lnurlc", "lnurlw", "lnurlp", "keyauth"]
#         return any(self.scheme == uri for uri in uris)

#     @property
#     def query_params(self) -> dict[str, str]:
#         return {k: v[0] for k, v in parse_qs(self.query).items()}

#     @property
#     def insecure(self) -> bool:
#         if not self.host:
#             return True
#         return self.scheme == "http" or self.host in INSECURE_HOSTS or self.host.endswith(".onion")

#     @classmethod
#     def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
#         return core_schema.chain_schema(
#             [
#                 core_schema.no_info_plain_validator_function(ctrl_characters_validator),
#                 core_schema.no_info_plain_validator_function(strict_rfc3986_validator),
#                 core_schema.no_info_plain_validator_function(validate_lnurl_host),
#             ]
#         )


class LightningInvoice(Bech32):
    """Bech32 Lightning invoice."""


class LightningNodeUri(str):
    """Remote node address of form `node_key@ip_address:port_number`."""

    __slots__ = ("username", "host", "port")

    def __new__(cls, uri: str, **_) -> "LightningNodeUri":
        return str.__new__(cls, uri)

    def __init__(
        self,
        uri: str,
        username: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[str] = None,
    ):
        str.__init__(uri)
        self.username, self.host, self.port = (
            (username, host, port) if username and host and port else self.__get_parts__(uri)
        )

    @classmethod
    def __get_parts__(cls, uri: str) -> tuple[str, str, str]:
        match = re.fullmatch(r"(?P<username>[^@:\s]+)@(?P<host>[^@:\s]+):(?P<port>[^@:\s]+)", uri)
        if not match:
            raise ValueError("Invalid Lightning node URI.")
        return match.group("username"), match.group("host"), match.group("port")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:

        def validate(value: Any):
            username, host, port = cls.__get_parts__(str(value))
            return cls(str(value), username=username, host=host, port=port)

        def serialize(value: Any) -> str:
            return str(value)

        return core_schema.no_info_after_validator_function(
            validate,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(cls),
                    core_schema.str_schema(),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(serialize, when_used="json"),
        )


class Lnurl(str):
    url: Url
    lud17_prefix: Optional[str] = None

    def __new__(cls, lightning: str) -> Lnurl:
        url = cls.clean(lightning)
        return str.__new__(cls, str(url))

    def __init__(self, lightning: str):
        url = self.clean(lightning)
        if not url.host:
            raise InvalidUrl("URL must have a valid host.")
        is_lud17 = any(url.scheme == uri for uri in LUD17_SCHEMES)
        if not is_lud17:
            self.url = TypeAdapter(Url).validate_python(str(url))
            self.lud17_prefix = None
            return str.__init__(str(url))
        self.lud17_prefix = url.scheme
        insecure = url.host in INSECURE_HOSTS or url.host.endswith(".onion")
        _replace = "http" if insecure else "https"
        _url = str(url)
        _url = _url.replace(url.scheme, _replace, 1)
        self.url = TypeAdapter(Url).validate_python(_url)
        return str.__init__(_url)

    @classmethod
    def clean(cls, lightning: str) -> Url:
        lightning = _lnurl_clean(lightning)
        if lightning.lower().startswith("lnurl1"):
            url = TypeAdapter(Url).validate_python(url_decode(lightning))
            return url
        url = TypeAdapter(Url).validate_python(lightning)
        return url

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:

        def validate(value: Any):
            _ = cls.clean(value)
            return cls(value)

        def serialize(value: Any) -> str:
            return str(value)

        return core_schema.no_info_after_validator_function(
            validate,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(cls),
                    core_schema.str_schema(),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(serialize, when_used="json"),
        )

    @property
    def bech32(self) -> Bech32:
        """Returns Bech32 representation of the Lnurl if it is a Bech32 encoded URL."""
        url = url_encode(str(self.url))
        return TypeAdapter(Bech32).validate_python(url)

    # LUD-04: auth base spec.
    @property
    def is_login(self) -> bool:
        return any(k == "tag" and v == "login" for k, v in self.url.query_params())

    # LUD-08: Fast withdrawRequest.
    @property
    def is_fast_withdraw(self) -> bool:
        q: dict[str, str] = {}
        for k, v in self.url.query_params():
            q[k] = v
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
        return self.lud17_prefix is not None

    @property
    def lud17(self) -> Optional[str]:
        if not self.lud17_prefix:
            return None
        _url = str(self.url)
        return _url.replace(self.url.scheme, self.lud17_prefix, 1)


# LUD-16: Paying to static internet identifiers.
class LnAddress(str):
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

    def is_valid_lnaddress(self, address: str) -> bool:
        # A user can then type these on a WALLET. The <username> is limited
        # to a-z-1-9-_.. Please note that this is way more strict than common
        # email addresses as it allows fewer symbols and only lowercase characters.
        lnaddress_regex = r"[a-z0-9\._%+-]+@[A-Za-z0-9\.-]+\.[A-Za-z]{2,63}"
        return re.fullmatch(lnaddress_regex, address) is not None

    @classmethod
    def __get_url__(cls, address: str) -> CallbackUrl:
        name, domain = address.split("@")
        url = ("http://" if domain.endswith(".onion") else "https://") + domain + "/.well-known/lnurlp/" + name
        return TypeAdapter(CallbackUrl).validate_python(url)


class LnurlPayMetadata(str):
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
            TypeAdapter(Json[list[tuple[str, str]]]).validate_python(json_str)
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
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:

        def validate(value: Any):
            return cls(value, json_obj=cls.__validate_metadata__(str(value)))

        def serialize(value: Any) -> str:
            return str(value)

        return core_schema.no_info_after_validator_function(
            validate,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(cls),
                    core_schema.str_schema(),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(serialize, when_used="json"),
        )

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


InitializationVectorBase64 = Annotated[str, StringConstraints(min_length=24, max_length=24)]
CiphertextBase64 = Annotated[str, StringConstraints(min_length=24, max_length=4096)]
Max144Str = Annotated[str, StringConstraints(max_length=144)]


class MilliSatoshi(int):
    """A thousandth of a satoshi."""

    @classmethod
    def from_btc(cls, btc: Decimal) -> MilliSatoshi:
        return cls(btc * 100_000_000_000)

    @property
    def btc(self) -> Decimal:
        return Decimal(self) / 100_000_000_000

    @property
    def sat(self) -> int:
        return self // 1000

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.int_schema(),
        )


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


def validate_paylink_is_lud17(value: Optional[str] = None) -> str | None:
    if not value:
        return None
    lnurl = Lnurl(value)
    if lnurl.is_lud17 and lnurl.lud17_prefix == "lnurlp":
        return value
    raise ValueError("`payLink` must be a valid LUD17 URL (lnurlp://).")


Lud17PayLink = Annotated[str, AfterValidator(validate_paylink_is_lud17)]
