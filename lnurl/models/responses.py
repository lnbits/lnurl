import json
import math

from hashlib import sha256
from pydantic import BaseModel, Field, validator
from pydantic.validators import str_validator
from typing import List, Optional, Tuple
from typing_extensions import Literal

from lnurl.exceptions import LnurlResponseException, InvalidLnurlPayMetadata
from .generics import HttpsUrl, LightningInvoiceBech32, LightningNodeUri, Millisatoshi


class LnurlPayMetadata(str):
    valid_metadata_mime_types = ['text/plain']

    @classmethod
    def __get_validators__(cls):
        yield str_validator
        yield cls.validate
        yield cls.validate_raw_json

    @classmethod
    def validate(cls, value: str) -> 'LnurlPayMetadata':
        return cls(value)

    @classmethod
    def validate_raw_json(cls, value: str) -> str:
        # TODO: check and raise InvalidLnurlPayMetadata
        return value

    def load(self) -> List[Tuple[str, str]]:
        return [tuple(x) for x in json.loads(self) if x[0] in self.valid_metadata_mime_types]


class LnurlPayRoute(BaseModel):
    pass


class LnurlPaySuccessAction(BaseModel):
    pass


class LnurlResponseModel(BaseModel):

    class Config:
        allow_population_by_field_name = True

    def dict(self, **kwargs):
        kwargs.setdefault('by_alias', True)
        return super().dict(**kwargs)

    def json(self, **kwargs):
        kwargs.setdefault('by_alias', True)
        return super().json(**kwargs)

    @property
    def ok(self) -> bool:
        return not ('status' in self.__fields__ and self.status.lower() == 'error')


class LnurlErrorResponse(LnurlResponseModel):
    status: Literal['ERROR'] = 'ERROR'
    reason: str

    @property
    def error_msg(self) -> str:
        return self.reason


class LnurlSuccessResponse(LnurlResponseModel):
    status: Literal['OK'] = 'OK'


class LnurlAuthResponse(LnurlResponseModel):
    tag: Literal['login'] = 'login'
    callback: HttpsUrl
    k1: str


class LnurlChannelResponse(LnurlResponseModel):
    tag: Literal['channelRequest'] = 'channelRequest'
    uri: LightningNodeUri
    callback: HttpsUrl
    k1: str


class LnurlHostedChannelResponse(LnurlResponseModel):
    tag: Literal['hostedChannelRequest'] = 'hostedChannelRequest'
    uri: LightningNodeUri
    k1: str
    alias: Optional[str]


class LnurlPayResponse(LnurlResponseModel):
    tag: Literal['payRequest'] = 'payRequest'
    callback: HttpsUrl
    min_sendable: Millisatoshi = Field(..., alias='minSendable')
    max_sendable: Millisatoshi = Field(..., alias='maxSendable')
    metadata: LnurlPayMetadata

    @validator('max_sendable')
    def max_less_than_min(cls, v, values, **kwargs):
        if 'min_sendable' in values and v < values['min_sendable']:
            raise ValueError('`max_sendable` cannot be less than `min_sendable`.')
        return v

    @property
    def h(self) -> str:
        return sha256(self.metadata.encode('utf-8')).hexdigest()

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.min_sendable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.max_sendable / 1000))


class LnurlPayActionResponse(LnurlResponseModel):
    pr: LightningInvoiceBech32
    success_action: Optional[LnurlPaySuccessAction] = Field(None, alias='successAction')
    routes: List[LnurlPayRoute] = []


class LnurlWithdrawResponse(LnurlResponseModel):
    tag: Literal['withdrawRequest'] = 'withdrawRequest'
    callback: HttpsUrl
    k1: str
    min_withdrawable: Millisatoshi = Field(..., alias='minWithdrawable')
    max_withdrawable: Millisatoshi = Field(..., alias='maxWithdrawable')
    default_description: str = Field('', alias='defaultDescription')

    @validator('max_withdrawable')
    def max_less_than_min(cls, v, values, **kwargs):
        if 'min_withdrawable' in values and v < values['min_withdrawable']:
            raise ValueError('`max_withdrawable` cannot be less than `min_withdrawable`.')
        return v

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
            if 'status' in d and d['status'].lower() == 'error':
                return LnurlErrorResponse(**d)

            elif 'tag' in d:
                # some services return `status` here, but it is not in the spec
                d.pop('status', None)

                return {
                    'channelRequest': LnurlChannelResponse,
                    'hostedChannelRequest': LnurlHostedChannelResponse,
                    'payRequest': LnurlPayResponse,
                    'withdrawRequest': LnurlWithdrawResponse,
                }[d['tag']](**d)

            elif 'success_action' in d:
                return LnurlPayActionResponse(**d)

            else:
                return LnurlSuccessResponse(**d)

        except Exception:
            raise LnurlResponseException
