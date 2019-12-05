import json
import math

from hashlib import sha256
from pydantic import BaseModel, AnyUrl, HttpUrl, PositiveInt
from pydantic.validators import str_validator
from typing import List, Optional, Tuple, Union

from lnurl.exceptions import LnurlResponseException, InvalidLnurlTag, InvalidLnurlPayMetadata
from lnurl.utils import to_camel
from .generics import Bech32Invoice, HttpsUrl, LightningNodeUri, MilliSatoshi


class LnurlPayMetadata(str):

    @classmethod
    def __get_validators__(cls) -> 'LnurlPayMetadata':
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> 'LnurlPayMetadata':
        return cls(value)

    def load(self) -> List[Tuple[str, str]]:
        valid_metadata_mime_types = ['text/plain']
        return [tuple(x) for x in json.loads(self) if x[0] in valid_metadata_mime_types]


class LnurlPayRoute(BaseModel):
    pass


class LnurlPaySuccessAction(BaseModel):
    pass


class LnurlResponseModel(BaseModel):

    class Config:
        alias_generator = to_camel
        json_dumps = json.dumps

    @property
    def ok(self) -> bool:
        return not ('status' in self.__fields__ and self.status.lower() == 'error')


class LnurlErrorResponse(LnurlResponseModel):
    status: str = 'ERROR'
    reason: str

    @property
    def error_msg(self) -> str:
        return self.reason


class LnurlSuccessResponse(LnurlResponseModel):
    status: str = 'OK'


class LnurlAuthResponse(LnurlResponseModel):
    tag: str = 'login'


class LnurlChannelResponse(LnurlResponseModel):
    tag: str = 'channelRequest'
    uri: str  # TODO: LightningNodeUri
    callback: HttpsUrl
    k1: str


class LnurlHostedChannelResponse(LnurlResponseModel):
    tag: str = 'hostedChannelRequest'
    uri: str  # TODO: LightningNodeUri
    k1: str
    alias: Optional[str]


class LnurlPayResponse(LnurlResponseModel):
    tag: str = 'payRequest'
    callback: HttpsUrl
    min_sendable: MilliSatoshi
    max_sendable: MilliSatoshi
    metadata: LnurlPayMetadata

    @property
    def h(self) -> str:
        return sha256(self.metadata.encode('utf-8')).hexdigest()

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.min_sendable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.max_sendable / 1000))


class LnurlPaySuccessResponse(LnurlResponseModel):
    pr: Bech32Invoice
    success_action: Optional[LnurlPaySuccessAction]
    routes: List[LnurlPayRoute]


class LnurlWithdrawResponse(LnurlResponseModel):
    tag: str = 'withdrawRequest'
    callback: HttpsUrl
    k1: str
    min_withdrawable: MilliSatoshi
    max_withdrawable: MilliSatoshi
    default_description: str

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.min_withdrawable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.max_withdrawable / 1000))


class LnurlResponse:

    @staticmethod
    def from_dict(d) -> Union[LnurlSuccessResponse, LnurlErrorResponse]:
        try:
            if 'status' in d and d['status'].lower() == 'error':
                return LnurlErrorResponse(**d)

            elif 'tag' in d:
                return {
                    'login': LnurlAuthResponse,
                    'channelRequest': LnurlChannelResponse,
                    'hostedChannelRequest': LnurlHostedChannelResponse,
                    'payRequest': LnurlPayResponse,
                    'withdrawRequest': LnurlWithdrawResponse,
                }[d['tag']](**d)

            elif 'success_action' in d:
                return LnurlPaySuccessResponse(**d)

        except Exception:
            raise LnurlResponseException
