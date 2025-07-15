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
    LnAddress,
    Lnurl,
    LnurlPayMetadata,
    LnurlPaySuccessActionTag,
    LnurlResponseTag,
    LnurlStatus,
    Max144Str,
    Url,
)


class LnurlPayRouteHop(BaseModel):
    node_id: str = Field(alias="nodeId")
    channel_update: str = Field(alias="channelUpdate")


class LnurlPaySuccessAction(BaseModel, ABC):
    tag: LnurlPaySuccessActionTag


class MessageAction(LnurlPaySuccessAction):
    tag: LnurlPaySuccessActionTag = LnurlPaySuccessActionTag.message
    message: Max144Str


class UrlAction(LnurlPaySuccessAction):
    tag = LnurlPaySuccessActionTag.url
    url: Url
    description: Max144Str


# LUD-10: Add support for AES encrypted messages in payRequest.
class AesAction(LnurlPaySuccessAction):
    tag = LnurlPaySuccessActionTag.aes
    description: Max144Str
    ciphertext: CiphertextBase64
    iv: InitializationVectorBase64


class LnurlResponseModel(BaseModel):

    class Config:
        allow_population_by_field_name = True
        by_alias = True
        use_enum_values = True

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
    min_sendable: MilliSatoshi = Field(alias="minSendable", gt=0)
    max_sendable: MilliSatoshi = Field(alias="maxSendable", gt=0)
    metadata: LnurlPayMetadata
    # LUD-18: Payer identity in payRequest protocol.
    payer_data: Optional[LnurlPayResponsePayerData] = Field(alias="payerData")

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
    success_action: Optional[Union[AesAction, MessageAction, UrlAction]] = Field(default=None, alias="successAction")
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
    min_withdrawable: MilliSatoshi = Field(alias="minWithdrawable", ge=0)
    max_withdrawable: MilliSatoshi = Field(alias="maxWithdrawable", ge=0)
    default_description: str = Field(default="", alias="defaultDescription")
    # LUD-14: balanceCheck: reusable withdrawRequests
    balance_check: Optional[CallbackUrl] = Field(
        default=None, alias="balanceCheck", description="URL to check balance, (LUD-14)"
    )
    current_balance: Optional[MilliSatoshi] = Field(
        default=None, alias="currentBalance", description="Current balance, (LUD-14)"
    )
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
