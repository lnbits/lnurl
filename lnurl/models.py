import json
import math

from typing import List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from .exceptions import LnurlResponseException, InvalidLnurlTag, InvalidLnurlPayMetadata
from .utils import decode, snake_keys


class ParsedUrl:
    def __init__(self, url: str) -> None:
        self._parsed_url = urlparse(url)
        self.full = url
        self.base = f'{self._parsed_url.scheme}://{self._parsed_url.netloc}{self._parsed_url.path}'
        self.query_params = {k: v[0] for k, v in parse_qs(self._parsed_url.query).items()}

    def __repr__(self) -> str:
        return f'<ParsedUrl [{self.full}]>'

    def __str__(self) -> str:
        return self.full


class Lnurl:
    def __init__(self, lnurl: str, *, force_https: bool = True) -> None:
        self.bech32 = lnurl
        self.url = ParsedUrl(decode(lnurl, force_https=force_https))

    def __repr__(self) -> str:
        return f'<Lnurl [{self.bech32}]>'

    def __str__(self) -> str:
        return self.bech32

    @property
    def decoded(self) -> str:
        return self.url.full


class LnurlResponse:
    _tag = None

    def __init__(self, d: dict) -> None:
        self.__dict__ = snake_keys(d)

        if 'callback' in self.__dict__:
            self.callback = ParsedUrl(self.callback)

        if 'tag' in self.__dict__ and self.tag != self._tag:
            raise InvalidLnurlTag

    @property
    def ok(self) -> bool:
        """Returns True if :attr:`status` is "OK" or if we receive a tagged response from the server.
        """
        try:
            self.raise_for_status()
        except LnurlResponseException:
            return False
        return True

    @property
    def error_msg(self) -> Optional[str]:
        if 'status' in self.__dict__ and self.status == 'ERROR':
            return self.reason
        return None

    def raise_for_status(self) -> None:
        if self.error_msg:
            raise LnurlResponseException(self.error_msg)


class LnurlAuthResponse(LnurlResponse):
    _tag = 'login'

    def __init__(self, d) -> None:
        raise NotImplementedError


class LnurlChannelResponse(LnurlResponse):
    _tag = 'channelRequest'


class LnurlHostedChannelResponse(LnurlResponse):
    _tag = 'hostedChannelRequest'


class LnurlPayResponse(LnurlResponse):
    _tag = 'payRequest'
    _valid_metadata_mime_types = ['text/plain']

    def __init__(self, d: dict) -> None:
        super().__init__(d)

        if 'metadata' in self.__dict__:
            self.metadata = self.read_metadata(self.metadata)

    def read_metadata(self, json_str: str) -> List[Tuple]:
        try:
            return [tuple(x) for x in json.loads(json_str) if x[0] in self._valid_metadata_mime_types]
        except Exception:
            raise InvalidLnurlPayMetadata

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.min_sendable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.max_sendable / 1000))


class LnurlWithdrawResponse(LnurlResponse):
    _tag = 'withdrawRequest'

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.min_withdrawable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.max_withdrawable / 1000))
