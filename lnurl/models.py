import math

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union

try:
    from typing import Literal  # type: ignore
except ImportError:  # pragma: nocover
    from typing_extensions import Literal

from .exceptions import LnurlResponseException
from .types import (
    ClearnetUrl,
    InitializationVector,
    LightningInvoice,
    LightningNodeUri,
    LnurlPayMetadata,
    Max144Str,
    MilliSatoshi,
    OnionUrl,
)


class LnurlPayRouteHop(BaseModel):
    node_id: str = Field(..., alias="nodeId")
    channel_update: str = Field(..., alias="channelUpdate")


class LnurlPaySuccessAction(BaseModel):
    pass


class AesAction(LnurlPaySuccessAction):
    tag: Literal["aes"] = "aes"
    description: Max144Str
    ciphertext: str  # TODO
    iv: InitializationVector


class MessageAction(LnurlPaySuccessAction):
    tag: Literal["message"] = "message"
    message: Max144Str


class UrlAction(LnurlPaySuccessAction):
    tag: Literal["url"] = "url"
    url: Union[OnionUrl, ClearnetUrl]
    description: Max144Str


class LnurlResponseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True

    def dict(self, **kwargs):
        kwargs.setdefault("by_alias", True)
        return super().dict(**kwargs)

    def json(self, **kwargs):
        kwargs.setdefault("by_alias", True)
        return super().json(**kwargs)

    @property
    def ok(self) -> bool:
        return True


class LnurlErrorResponse(LnurlResponseModel):
    status: Literal["ERROR"] = "ERROR"
    reason: str

    @property
    def error_msg(self) -> str:
        return self.reason

    @property
    def ok(self) -> bool:
        return False


class LnurlSuccessResponse(LnurlResponseModel):
    status: Literal["OK"] = "OK"


class LnurlAuthResponse(LnurlResponseModel):
    tag: Literal["login"] = "login"
    callback: Union[OnionUrl, ClearnetUrl]
    k1: str


class LnurlChannelResponse(LnurlResponseModel):
    tag: Literal["channelRequest"] = "channelRequest"
    uri: LightningNodeUri
    callback: Union[OnionUrl, ClearnetUrl]
    k1: str


class LnurlHostedChannelResponse(LnurlResponseModel):
    tag: Literal["hostedChannelRequest"] = "hostedChannelRequest"
    uri: LightningNodeUri
    k1: str
    alias: Optional[str]


class LnurlPayResponse(LnurlResponseModel):
    tag: Literal["payRequest"] = "payRequest"
    callback: Union[OnionUrl, ClearnetUrl]
    min_sendable: MilliSatoshi = Field(..., alias="minSendable")
    max_sendable: MilliSatoshi = Field(..., alias="maxSendable")
    metadata: LnurlPayMetadata

    @validator("max_sendable")
    def max_less_than_min(cls, value, values, **kwargs):  # noqa
        if "min_sendable" in values and value < values["min_sendable"]:
            raise ValueError("`max_sendable` cannot be less than `min_sendable`.")
        return value

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.min_sendable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.max_sendable / 1000))


class LnurlPayActionResponse(LnurlResponseModel):
    pr: LightningInvoice
    success_action: Optional[Union[MessageAction, UrlAction, AesAction]] = Field(None, alias="successAction")
    routes: List[List[LnurlPayRouteHop]] = []


class LnurlWithdrawResponse(LnurlResponseModel):
    tag: Literal["withdrawRequest"] = "withdrawRequest"
    callback: Union[OnionUrl, ClearnetUrl]
    k1: str
    min_withdrawable: MilliSatoshi = Field(..., alias="minWithdrawable")
    max_withdrawable: MilliSatoshi = Field(..., alias="maxWithdrawable")
    default_description: str = Field("", alias="defaultDescription")

    @validator("max_withdrawable")
    def max_less_than_min(cls, value, values, **kwargs):  # noqa
        if "min_withdrawable" in values and value < values["min_withdrawable"]:
            raise ValueError("`max_withdrawable` cannot be less than `min_withdrawable`.")
        return value

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.min_withdrawable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.max_withdrawable / 1000))


class LnurlResponse:
    @staticmethod
    def from_dict(d: dict) -> LnurlResponseModel:
        try:
            if "tag" in d:
                # some services return `status` here, but it is not in the spec
                d.pop("status", None)

                return {
                    "channelRequest": LnurlChannelResponse,
                    "hostedChannelRequest": LnurlHostedChannelResponse,
                    "payRequest": LnurlPayResponse,
                    "withdrawRequest": LnurlWithdrawResponse,
                }[d["tag"]](**d)

            if "successAction" in d:
                d.pop("status", None)
                return LnurlPayActionResponse(**d)

            # some services return `status` in lowercase, but spec says upper
            d["status"] = d["status"].upper()

            if "status" in d and d["status"] == "ERROR":
                return LnurlErrorResponse(**d)

            return LnurlSuccessResponse(**d)

        except Exception:
            raise LnurlResponseException
