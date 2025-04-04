LNURL implementation for Python
===============================

[![github-tests-badge]][github-tests]
[![github-mypy-badge]][github-mypy]
[![codecov-badge]][codecov]
[![pypi-badge]][pypi]
[![pypi-versions-badge]][pypi]
[![license-badge]](LICENSE)


A collection of helpers for building [LNURL][lnurl] support into wallets and services.


LUDS support
------------

Check out the LUDS repository: [luds](https://github.com/lnurl/luds/)

- [x] LUD-01 - Base LNURL encoding and decoding
- [x] LUD-02 - channelRequest base spec
- [x] LUD-03 - withdrawRequest base spec
- [x] LUD-04 - Auth base spec
- [x] LUD-05 - BIP32-based seed generation for auth protocol
- [x] LUD-06 - payRequest base spec
- [x] LUD-07 - hostedChannelRequest base spec
- [x] LUD-08 - Fast withdrawRequest
- [x] LUD-09 - successAction field for payRequest
- [x] LUD-10 - aes success action in payRequest
- [x] LUD-11 - Disposable and storeable payRequests
- [x] LUD-12 - Comments in payRequest
- [x] LUD-13 - signMessage-based seed generation for auth protocol
- [x] LUD-14 - balanceCheck: reusable withdrawRequests
- [x] LUD-15 - balanceNotify: services hurrying up the withdraw process
- [x] LUD-16 - Paying to static internet identifiers
- [x] LUD-17 - Scheme prefixes and raw (non bech32-encoded) URLs
- [x] LUD-18 - Payer identity in payRequest protocol
- [x] LUD-19 - Pay link discoverable from withdraw link
- [x] LUD-20 - Long payment description for pay protocol
- [x] LUD-21 - verify LNURL-pay payments


Configuration
-------------

Developers can force strict RFC3986 validation for the URLs that the library encodes/decodes, using this env var:

> LNURL_STRICT_RFC3986 = "0" by default (False)


Basic usage
-----------

```python
>>> import lnurl
>>> lnurl.encode('https://service.io/?q=3fc3645b439ce8e7')
Lnurl('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9', bech32=Bech32('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9', hrp='lnurl', data=[13, 1, 26, 7, 8, 28, 3, 19, 7, 8, 23, 18, 30, 28, 27, 5, 14, 9, 27, 6, 18, 24, 27, 5, 5, 25, 20, 22, 30, 11, 25, 31, 14, 4, 30, 19, 6, 25, 19, 3, 6, 12, 27, 3, 8, 13, 11, 2, 6, 16, 25, 19, 18, 24, 27, 5, 7, 1, 18, 19, 14]), url=WebUrl('https://service.io/?q=3fc3645b439ce8e7', scheme='https', host='service.io', tld='io', host_type='domain', path='/', query='q=3fc3645b439ce8e7'))
>>> lnurl.decode('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9')
WebUrl('https://service.io/?q=3fc3645b439ce8e7', scheme='https', host='service.io', tld='io', host_type='domain', path='/', query='q=3fc3645b439ce8e7')
```

The `Lnurl` object wraps a bech32 LNURL to provide some extra utilities.

```python
from lnurl import Lnurl

lnurl = Lnurl("LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9")
lnurl.bech32  # "LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9"
lnurl.bech32.hrp  # "lnurl"
lnurl.url  # "https://service.io/?q=3fc3645b439ce8e7"
lnurl.url.host  # "service.io"
lnurl.url.base  # "https://service.io/"
lnurl.url.query  # "q=3fc3645b439ce8e7"
lnurl.url.query_params  # {"q": "3fc3645b439ce8e7"}
```

Parsing LNURL responses
-----------------------

You can use a `LnurlResponse` to wrap responses you get from a LNURL.
The different types of responses defined in the [LNURL spec][lnurl-spec] have a different model
with different properties (see `models.py`):

```python
import httpx

from lnurl import Lnurl, LnurlResponse

lnurl = Lnurl('LNURL1DP68GURN8GHJ7MRWW4EXCTNZD9NHXATW9EU8J730D3H82UNV94MKJARGV3EXZAELWDJHXUMFDAHR6WFHXQERSVPCA649RV')
try:
  async with httpx.AsyncClient() as client:
    r = await client.get(lnurl.url)
    res = LnurlResponse.from_dict(r.json())  # LnurlPayResponse
    res.ok  # bool
    res.max_sendable  # int
    res.max_sats  # int
    res.callback.base  # str
    res.callback.query_params # dict
    res.metadata  # str
    res.metadata.list()  # list
    res.metadata.text  # str
    res.metadata.images  # list
r = requests.get(lnurl.url)
```

If you have already `httpx` installed, you can also use the `.handle()` function directly.
It will return the appropriate response for a LNURL.

```python
>>> import lnurl
>>> lnurl.handle('lightning:LNURL1DP68GURN8GHJ7MRWW4EXCTNZD9NHXATW9EU8J730D3H82UNV94CXZ7FLWDJHXUMFDAHR6V33XCUNSVE38QV6UF')
LnurlPayResponse(tag='payRequest', callback=WebUrl('https://lnurl.bigsun.xyz/lnurl-pay/callback/2169831', scheme='https', host='lnurl.bigsun.xyz', tld='xyz', host_type='domain', path='/lnurl-pay/callback/2169831'), min_sendable=10000, max_sendable=10000, metadata=LnurlPayMetadata('[["text/plain","NgHaEyaZNDnW iI DsFYdkI"],["image/png;base64","iVBOR...uQmCC"]]'))
```

You can execute and LNURL with either payRequest, withdrawRequest or login tag using the `execute` function.
```python
>>> import lnurl
>>> lnurl.execute('lightning:LNURL1DP68GURN8GHJ7MRWW4EXCTNZD9NHXATW9EU8J730D3H82UNV94CXZ7FLWDJHXUMFDAHR6V33XCUNSVE38QV6UF', 100000)
```

Building your own LNURL responses
---------------------------------

For LNURL services, the `lnurl` package can be used to build **valid** responses.

```python
from lnurl import LnurlWithdrawResponse

res = LnurlWithdrawResponse(
    callback="https://lnurl.bigsun.xyz/lnurl-withdraw/callback/9702808",
    k1="38d304051c1b76dcd8c5ee17ee15ff0ebc02090c0afbc6c98100adfa3f920874",
    min_withdrawable=551000,
    max_withdrawable=551000,
    default_description="sample withdraw",
)
res.json()  # str
res.dict()  # dict
```

All responses are [`pydantic`][pydantic] models, so the information you provide will be validated and you have
access to `.json()` and `.dict()` methods to export the data.

**Data is exported using :camel: camelCase keys by default, as per spec.**
You can also use camelCases when you parse the data, and it will be converted to snake_case to make your
Python code nicer.

If you want to export the data using :snake: snake_case (in your Python code, for example), you can change
the `by_alias` parameter: `res.dict(by_alias=False)` (it is `True` by default).


[github-tests]: https://github.com/lnbits/lnurl/actions?query=workflow%3Atests
[github-tests-badge]: https://github.com/lnbits/lnurl/workflows/tests/badge.svg
[github-mypy]: https://github.com/lnbits/lnurl/actions?query=workflow%3Amypy
[github-mypy-badge]: https://github.com/lnbits/lnurl/workflows/mypy/badge.svg
[codecov]: https://codecov.io/gh/lnbits/lnurl
[codecov-badge]: https://codecov.io/gh/lnbits/lnurl/branch/master/graph/badge.svg
[pypi]: https://pypi.org/project/lnurl/
[pypi-badge]: https://badge.fury.io/py/lnurl.svg
[pypi-versions-badge]: https://img.shields.io/pypi/pyversions/lnurl.svg
[license-badge]: https://img.shields.io/badge/license-MIT-blue.svg


CLI
---------
```console
$ poetry run lnurl
Usage: lnurl [OPTIONS] COMMAND [ARGS]...

  Python CLI for LNURL decode and encode lnurls

Options:
  --help  Show this message and exit.

Commands:
  decode           decode a LNURL
  encode           encode a URL
  handle           handle a LNURL
  execute          execute a LNURL
```
