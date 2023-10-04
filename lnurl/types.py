import json
import os
import re
from hashlib import sha256
from typing import Annotated, List, Optional, Tuple, Union

from pydantic import Field, HttpUrl, Json, PositiveInt, TypeAdapter, UrlConstraints, ValidationError
from pydantic.functional_validators import AfterValidator

from .exceptions import InvalidLnurlPayMetadata
from .helpers import _bech32_decode, _lnurl_clean, _lnurl_decode


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

    # @classmethod
    # def __get_validators__(cls):
    #     # yield str_validator
    #     yield cls.validate

    @classmethod
    def validate(cls, value: str) -> "Bech32":
        hrp, data = cls.__get_data__(value)
        return cls(value, hrp=hrp, data=data)


def ctrl_characters_validator(value: str) -> str:
    """Checks for control characters (unicode blocks C0 and C1, plus DEL)."""
    if re.compile(r"[\u0000-\u001f\u007f-\u009f]").search(value):
        raise ValidationError
    return value


def strict_rfc3986_validator(value: str) -> str:
    """Checks for RFC3986 compliance."""
    if os.environ.get("LNURL_STRICT_RFC3986", "0") == "1":
        if re.compile(r"[^]a-zA-Z0-9._~:/?#[@!$&'()*+,;=-]").search(value):
            raise ValidationError
    return value


# Secure web URL
ClearnetUrl = Annotated[
    HttpUrl,
    UrlConstraints(
        max_length=2047,  # https://stackoverflow.com/questions/417142/
        allowed_schemes=["https"],
    ),
    AfterValidator(ctrl_characters_validator),
    AfterValidator(strict_rfc3986_validator),
]


def onion_validator(value: str) -> None:
    """checks if it is a valid onion address"""
    if not value.endswith(".onion"):
        raise ValidationError


# Tor anonymous onion service
OnionUrl = Annotated[
    HttpUrl,
    UrlConstraints(
        max_length=2047,  # https://stackoverflow.com/questions/417142/
        allowed_schemes=["http"],
    ),
    AfterValidator(ctrl_characters_validator),
    AfterValidator(strict_rfc3986_validator),
    AfterValidator(onion_validator),
]


def localhost_validator(value: str) -> None:
    # host, tld, host_type, rebuild = super().validate_host(parts)
    if not value.find("127.0.0.1") or not value.find("0.0.0.0"):
        raise ValidationError


# Unsecure web URL, to make developers life easier
DebugUrl = Annotated[
    HttpUrl,
    UrlConstraints(
        max_length=2047,  # https://stackoverflow.com/questions/417142/
        allowed_schemes=["http"],
    ),
    AfterValidator(ctrl_characters_validator),
    AfterValidator(strict_rfc3986_validator),
    AfterValidator(localhost_validator),
]


class LightningInvoice(Bech32):
    """Bech32 Lightning invoice."""

    @property
    def amount(self) -> int:
        raise NotImplementedError

    @property
    def prefix(self) -> str:
        raise NotImplementedError

    @property
    def h(self):
        raise NotImplementedError


class LightningNodeUri(ReprMixin, str):
    """Remote node address of form `node_key@ip_address:port_number`."""

    # __slots__ = ("key", "ip", "port")

    # def __new__(cls, uri: str, **_) -> "LightningNodeUri":
    #     return str.__new__(cls, uri)

    # def __init__(self, uri: str, *, key: Optional[str] = None, ip: Optional[str] = None, port: Optional[str] = None):
    #     str.__init__(uri)
    #     self.key = key
    #     self.ip = ip
    #     self.port = port

    # @classmethod
    # def __get_validators__(cls):
    #     yield str_validator
    #     yield cls.validate

    # @classmethod
    # def validate(cls, value: str) -> "LightningNodeUri":
    #     try:
    #         key, netloc = value.split("@")
    #         ip, port = netloc.split(":")
    #     except Exception:
    #         raise ValueError

    #     return cls(value, key=key, ip=ip, port=port)


class Lnurl(ReprMixin, str):
    __slots__ = ("bech32", "url")

    def __new__(cls, lightning: str, **_) -> "Lnurl":
        return str.__new__(cls, _lnurl_clean(lightning))

    def __init__(self, lightning: str, *, url: Optional[Union[OnionUrl, ClearnetUrl, DebugUrl]] = None):
        bech32 = _lnurl_clean(lightning)
        str.__init__(bech32)
        self.bech32 = Bech32(bech32)
        self.url = url if url else self.__get_url__(bech32)

    @classmethod
    def __get_url__(cls, bech32: str) -> Union[OnionUrl, ClearnetUrl, DebugUrl]:
        url: str = _lnurl_decode(bech32)
        adapter = TypeAdapter(Union[OnionUrl, ClearnetUrl, DebugUrl])
        return adapter.validate_python(url)

    # @classmethod
    # def __get_validators__(cls):
    #     yield str_validator
    #     yield cls.validate

    @classmethod
    def validate(cls, value: str) -> "Lnurl":
        return cls(value, url=cls.__get_url__(value))

    @property
    def is_login(self) -> bool:
        params = {k: v for k, v in self.url.query_params()}
        return params.get("tag") == "login"


class LnurlPayMetadata(ReprMixin, str):
    valid_metadata_mime_types = {"text/plain", "image/png;base64", "image/jpeg;base64"}

    __slots__ = ("_list",)

    def __new__(cls, json_str: str, **_) -> "LnurlPayMetadata":
        return str.__new__(cls, json_str)

    def __init__(self, json_str: str, *, json_obj: Optional[List] = None):
        str.__init__(json_str)
        self._list = json_obj if json_obj else self.__validate_metadata__(json_str)

    @classmethod
    def __validate_metadata__(cls, json_str: str) -> List[Tuple[str, str]]:
        try:
            adapter = TypeAdapter(Json[List[Tuple[str, str]]])
            adapter.validate_python(json_str)
            data = [(str(item[0]), str(item[1])) for item in json.loads(json_str)]
        except ValidationError:
            raise InvalidLnurlPayMetadata

        clean_data = [x for x in data if x[0] in cls.valid_metadata_mime_types]
        mime_types = [x[0] for x in clean_data]
        counts = {x: mime_types.count(x) for x in mime_types}

        if not clean_data or "text/plain" not in mime_types or counts["text/plain"] > 1:
            raise InvalidLnurlPayMetadata

        return clean_data

    # @classmethod
    # def __get_validators__(cls):
    #     yield str_validator
    #     yield cls.validate

    @classmethod
    def validate(cls, value: str) -> "LnurlPayMetadata":
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


InitializationVector = Annotated[str, Field(max_length=24, min_length=24)]
Max144Str = Annotated[str, Field(max_length=144)]


class MilliSatoshi(PositiveInt):
    """A thousandth of a satoshi."""
