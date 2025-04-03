from __future__ import annotations

import math
from typing import List, Literal, Optional, Union

from bolt11 import MilliSatoshi
from pydantic import BaseModel, Field, ValidationError, validator

from .exceptions import LnurlResponseException
from .types import (
    CallbackUrl,
    CiphertextBase64,
    InitializationVectorBase64,
    LightningInvoice,
    LightningNodeUri,
    LnAddress,
    Lnurl,
    LnurlPayMetadata,
    Max144Str,
    Url,
)


class LnurlPayRouteHop(BaseModel):
    node_id: str = Field(alias="nodeId")
    channel_update: str = Field(alias="channelUpdate")


# LUD-9: Add successAction field to payRequest.
class LnurlPaySuccessAction(BaseModel):
    """Base class for all success actions"""


class MessageAction(LnurlPaySuccessAction):
    tag: Literal["message"] = "message"
    message: Max144Str


class UrlAction(LnurlPaySuccessAction):
    tag: Literal["url"] = "url"
    url: Url
    description: Max144Str


# LUD-10: Add support for AES encrypted messages in payRequest.
class AesAction(LnurlPaySuccessAction):
    tag: Literal["aes"] = "aes"
    description: Max144Str
    ciphertext: CiphertextBase64
    iv: InitializationVectorBase64


class LnurlResponseModel(BaseModel):

    class Config:
        allow_population_by_field_name = True
        by_alias = True

    def dict(self, **kwargs):
        kwargs.setdefault("by_alias", True)
        kwargs["exclude_none"] = True
        return super().dict(**kwargs)

    def json(self, **kwargs):
        kwargs.setdefault("by_alias", True)
        kwargs["exclude_none"] = True
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


# LUD-04: auth base spec.
class LnurlAuthResponse(LnurlResponseModel):
    tag: Literal["login"] = "login"
    callback: CallbackUrl
    k1: str


# LUD-2: channelRequest base spec.
class LnurlChannelResponse(LnurlResponseModel):
    tag: Literal["channelRequest"] = "channelRequest"
    uri: LightningNodeUri
    callback: CallbackUrl
    k1: str


# LUD-07: hostedChannelRequest base spec.
class LnurlHostedChannelResponse(LnurlResponseModel):
    tag: Literal["hostedChannelRequest"] = "hostedChannelRequest"
    uri: LightningNodeUri
    k1: str
    alias: Optional[str] = None


class LnurlPayResponse(LnurlResponseModel):
    tag: Literal["payRequest"] = "payRequest"
    callback: CallbackUrl
    min_sendable: MilliSatoshi = Field(alias="minSendable", gt=0)
    max_sendable: MilliSatoshi = Field(alias="maxSendable", gt=0)
    metadata: LnurlPayMetadata

    # Adds the optional comment_allowed field to the LnurlPayResponse
    # ref LUD-12: Comments in payRequest.
    comment_allowed: Optional[int] = Field(
        default=None,
        description="Length of comment which can be sent",
        alias="commentAllowed",
    )

    @validator("max_sendable")
    def max_less_than_min(cls, value, values):  # noqa
        if "min_sendable" in values and value < values["min_sendable"]:
            raise ValueError("`max_sendable` cannot be less than `min_sendable`.")
        return value

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.min_sendable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.max_sendable / 1000))

    def is_valid_amount(self, amount_msat: int) -> bool:
        return self.min_sendable <= amount_msat <= self.max_sendable


class LnurlPayActionResponse(LnurlResponseModel):
    pr: LightningInvoice
    # LUD-9: successAction field for payRequest.
    success_action: Optional[Union[MessageAction, UrlAction, AesAction]] = Field(default=None, alias="successAction")
    routes: List[List[LnurlPayRouteHop]] = []
    # LUD-11: Disposable and storeable payRequests.
    # If disposable is null, it should be interpreted as true,
    # so if SERVICE intends its LNURL links to be stored it must return disposable: false.
    disposable: Optional[bool] = None
    verify: Optional[str] = None


class LnurlWithdrawResponse(LnurlResponseModel):
    tag: Literal["withdrawRequest"] = "withdrawRequest"
    callback: CallbackUrl
    k1: str
    min_withdrawable: MilliSatoshi = Field(alias="minWithdrawable", ge=0)
    max_withdrawable: MilliSatoshi = Field(alias="maxWithdrawable", ge=0)
    default_description: str = Field(default="", alias="defaultDescription")
    # LUD-14: balanceCheck: reusable withdrawRequests
    balance_check: Optional[CallbackUrl] = Field(
        default=None, alias="balanceCheck", description="URL to check balance, (LUD-14)"
    )
    current_balance: Optional[MilliSatoshi] = Field(default=None, alias="currentBalance")
    # LUD-19: Pay link discoverable from withdraw link.
    pay_link: Optional[Union[LnAddress, Lnurl]] = Field(
        default=None, alias="payLink", description="Pay link discoverable from withdraw link. (LUD-19)"
    )

    @validator("max_withdrawable")
    def max_less_than_min(cls, value, values):
        if "min_withdrawable" in values and value < values["min_withdrawable"]:
            raise ValueError("`max_withdrawable` cannot be less than `min_withdrawable`.")
        return value

    # LUD-08: Fast withdrawRequest.
    @property
    def fast_withdraw_query(self) -> str:
        return "&".join([f"{k}={v}" for k, v in self.dict().items()])

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.min_withdrawable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.max_withdrawable / 1000))

    def is_valid_amount(self, amount: int) -> bool:
        return self.min_withdrawable <= amount <= self.max_withdrawable


class LnurlResponse:
    @staticmethod
    def from_dict(data: dict) -> LnurlResponseModel:
        tag = data.get("tag")

        # some services return `status` here, but it is not in the spec
        if tag or "successAction" in data:
            data.pop("status", None)

        try:
            if tag == "channelRequest":
                return LnurlChannelResponse(**data)
            if tag == "hostedChannelRequest":
                return LnurlHostedChannelResponse(**data)
            if tag == "payRequest":
                return LnurlPayResponse(**data)
            if tag == "withdrawRequest":
                return LnurlWithdrawResponse(**data)
            if "successAction" in data:
                return LnurlPayActionResponse(**data)
        except ValidationError as exc:
            raise LnurlResponseException(str(exc)) from exc

        status = data.get("status")
        if status is None or status == "":
            raise LnurlResponseException("Expected Success or Error response. But no `status` given.")

        # some services return `status` in lowercase, but spec says upper
        status = status.upper()

        if status == "OK":
            return LnurlSuccessResponse(status=status)

        if status == "ERROR":
            return LnurlErrorResponse(status=status, reason=data.get("reason", "Unknown error"))

        # if we reach here, it's an unknown response
        raise LnurlResponseException(f"Unknown response: {data}")
