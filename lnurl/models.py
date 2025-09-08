from __future__ import annotations

import math
from abc import ABC
from typing import Optional, Union

from bolt11 import MilliSatoshi
from pydantic import BaseModel, Field, ValidationError, validator

from .exceptions import LnurlResponseException
from .types import (
    CallbackUrl,
    CiphertextBase64,
    InitializationVectorBase64,
    LightningInvoice,
    LightningNodeUri,
    Lnurl,
    LnurlPayMetadata,
    LnurlPaySuccessActionTag,
    LnurlResponseTag,
    LnurlStatus,
    Max144Str,
    Url,
)


class LnurlPayRouteHop(BaseModel):
    nodeId: str
    channelUpdate: str


class LnurlPaySuccessAction(BaseModel, ABC):
    tag: LnurlPaySuccessActionTag


class MessageAction(LnurlPaySuccessAction):
    tag: LnurlPaySuccessActionTag = LnurlPaySuccessActionTag.message
    message: Max144Str


class UrlAction(LnurlPaySuccessAction):
    tag: LnurlPaySuccessActionTag = LnurlPaySuccessActionTag.url
    url: Url
    description: Max144Str


# LUD-10: Add support for AES encrypted messages in payRequest.
class AesAction(LnurlPaySuccessAction):
    tag: LnurlPaySuccessActionTag = LnurlPaySuccessActionTag.aes
    description: Max144Str
    ciphertext: CiphertextBase64
    iv: InitializationVectorBase64


class LnurlResponseModel(BaseModel):

    class Config:
        use_enum_values = True
        extra = "forbid"

    def dict(self, **kwargs):
        kwargs["exclude_none"] = True
        return super().dict(**kwargs)

    def json(self, **kwargs):
        kwargs["exclude_none"] = True
        return super().json(**kwargs)

    @property
    def ok(self) -> bool:
        return True


class LnurlErrorResponse(LnurlResponseModel):
    status: LnurlStatus = LnurlStatus.error
    reason: str

    @property
    def error_msg(self) -> str:
        return self.reason

    @property
    def ok(self) -> bool:
        return False


class LnurlSuccessResponse(LnurlResponseModel):
    status: LnurlStatus = LnurlStatus.ok


# LUD-21: verify base spec.
class LnurlPayVerifyResponse(LnurlSuccessResponse):
    pr: LightningInvoice = Field(description="Payment request")
    settled: bool = Field(description="Settled status of the payment")
    preimage: Optional[str] = Field(default=None, description="Preimage of the payment")


# LUD-04: auth base spec.
class LnurlAuthResponse(LnurlResponseModel):
    tag: LnurlResponseTag = LnurlResponseTag.login
    callback: CallbackUrl
    k1: str


# LUD-2: channelRequest base spec.
class LnurlChannelResponse(LnurlResponseModel):
    tag: LnurlResponseTag = LnurlResponseTag.channelRequest
    uri: LightningNodeUri
    callback: CallbackUrl
    k1: str


# LUD-07: hostedChannelRequest base spec.
class LnurlHostedChannelResponse(LnurlResponseModel):
    tag: LnurlResponseTag = LnurlResponseTag.hostedChannelRequest
    uri: LightningNodeUri
    k1: str
    alias: Optional[str] = None


# LUD-18: Payer identity in payRequest protocol.
class LnurlPayResponsePayerDataOption(BaseModel):
    mandatory: bool


class LnurlPayResponsePayerDataOptionAuth(LnurlPayResponsePayerDataOption):
    k1: str


class LnurlPayResponsePayerDataExtra(BaseModel):
    name: str
    field: LnurlPayResponsePayerDataOption


class LnurlPayResponsePayerData(BaseModel):
    name: Optional[LnurlPayResponsePayerDataOption] = None
    pubkey: Optional[LnurlPayResponsePayerDataOption] = None
    identifier: Optional[LnurlPayResponsePayerDataOption] = None
    email: Optional[LnurlPayResponsePayerDataOption] = None
    auth: Optional[LnurlPayResponsePayerDataOptionAuth] = None
    extras: Optional[list[LnurlPayResponsePayerDataExtra]] = None


class LnurlPayerDataAuth(BaseModel):
    key: str
    k1: str
    sig: str


class LnurlPayerData(BaseModel):
    name: Optional[str] = None
    pubkey: Optional[str] = None
    identifier: Optional[str] = None
    email: Optional[str] = None
    auth: Optional[LnurlPayerDataAuth] = None
    extras: Optional[dict] = None


class LnurlPayResponse(LnurlResponseModel):
    tag: LnurlResponseTag = LnurlResponseTag.payRequest
    callback: CallbackUrl
    minSendable: MilliSatoshi = Field(gt=0)
    maxSendable: MilliSatoshi = Field(gt=0)
    metadata: LnurlPayMetadata
    # LUD-18: Payer identity in payRequest protocol.
    payerData: Optional[LnurlPayResponsePayerData] = None
    # Adds the optional comment_allowed field to the LnurlPayResponse
    # ref LUD-12: Comments in payRequest.
    commentAllowed: Optional[int] = None

    # NIP-57 Lightning Zaps
    allowsNostr: Optional[bool] = None
    nostrPubkey: Optional[str] = None

    @validator("maxSendable")
    def max_less_than_min(cls, value, values):  # noqa
        if "minSendable" in values and value < values["minSendable"]:
            raise ValueError("`maxSendable` cannot be less than `minSendable`.")
        return value

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.minSendable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.maxSendable / 1000))

    def is_valid_amount(self, amount_msat: int) -> bool:
        return self.minSendable <= amount_msat <= self.maxSendable


class LnurlPayActionResponse(LnurlResponseModel):
    pr: LightningInvoice
    # LUD-9: successAction field for payRequest.
    successAction: Optional[Union[AesAction, MessageAction, UrlAction]] = None
    routes: list[list[LnurlPayRouteHop]] = []
    # LUD-11: Disposable and storeable payRequests.
    # If disposable is null, it should be interpreted as true.
    # so if SERVICE intends its LNURL links to be stored it must return disposable=False.
    disposable: Optional[bool] = Field(default=None, description="LUD-11: Disposable and storeable payRequests.")
    # LUD-21: verify base spec.
    verify: Optional[CallbackUrl] = Field(default=None, description="LUD-21: verify base spec.")


class LnurlWithdrawResponse(LnurlResponseModel):
    tag: LnurlResponseTag = LnurlResponseTag.withdrawRequest
    callback: CallbackUrl
    k1: str
    minWithdrawable: MilliSatoshi = Field(ge=0)
    maxWithdrawable: MilliSatoshi = Field(ge=0)
    defaultDescription: str = ""
    # LUD-14: balanceCheck: reusable withdrawRequests
    balanceCheck: Optional[CallbackUrl] = None
    currentBalance: Optional[MilliSatoshi] = None
    # LUD-19: Pay link discoverable from withdraw link.
    payLink: Optional[str] = None

    @validator("payLink", pre=True)
    def paylink_must_be_lud17(cls, value: Optional[str] = None) -> str | None:
        if not value:
            return None
        lnurl = Lnurl(value)
        if lnurl.is_lud17 and lnurl.lud17_prefix == "lnurlp":
            return value
        raise ValueError("`payLink` must be a valid LUD17 URL (lnurlp://).")

    @validator("maxWithdrawable")
    def max_less_than_min(cls, value, values):
        if "minWithdrawable" in values and value < values["minWithdrawable"]:
            raise ValueError("`maxWithdrawable` cannot be less than `minWithdrawable`.")
        return value

    # LUD-08: Fast withdrawRequest.
    @property
    def fast_withdraw_query(self) -> str:
        return "&".join([f"{k}={v}" for k, v in self.dict().items()])

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.minWithdrawable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.maxWithdrawable / 1000))

    def is_valid_amount(self, amount: int) -> bool:
        return self.minWithdrawable <= amount <= self.maxWithdrawable


def is_pay_action_response(data: dict) -> bool:
    return "pr" in data and "routes" in data


class LnurlResponse:

    @staticmethod
    def from_dict(data: dict) -> LnurlResponseModel:
        tag = data.get("tag")

        # drop status field from all responses with a tag
        # some services return `status` in responses with a tag
        if tag or is_pay_action_response(data):
            data.pop("status", None)

        try:
            if tag == "channelRequest":
                return LnurlChannelResponse(**data)
            elif tag == "hostedChannelRequest":
                return LnurlHostedChannelResponse(**data)
            elif tag == "payRequest":
                return LnurlPayResponse(**data)
            elif tag == "withdrawRequest":
                return LnurlWithdrawResponse(**data)
            elif is_pay_action_response(data):
                return LnurlPayActionResponse(**data)

        except ValidationError as exc:
            raise LnurlResponseException(str(exc)) from exc

        status = data.get("status")
        if status is None or status == "":
            raise LnurlResponseException("Expected Success or Error response. But no `status` given.")

        # some services return `status` in lowercase, but spec says upper
        status = status.upper()

        if status == "OK":
            return LnurlSuccessResponse(status=LnurlStatus.ok)

        if status == "ERROR":
            return LnurlErrorResponse(status=LnurlStatus.error, reason=data.get("reason", "Unknown error"))

        # if we reach here, it's an unknown response
        raise LnurlResponseException(f"Unknown response: {data}")
