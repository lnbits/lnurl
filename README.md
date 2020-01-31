LNURL implementation for Python
===============================

[![travis-badge]][travis]
[![codecov-badge]][codecov]
[![pypi-badge]][pypi]
[![pypi-versions]][pypi]
[![license-badge]](LICENSE)

A collection of helpers for building [LNURL][lnurl] support into wallets and services.

Basic usage
-----------

```python
>>> import lnurl
>>> lnurl.encode('https://service.io/?q=3fc3645b439ce8e7')
Lnurl('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9', url=Url('https://service.io/?q=3fc3645b439ce8e7', scheme='https', host='service.io', tld='io', host_type='domain', path='/', query='q=3fc3645b439ce8e7'))
>>> lnurl.decode('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9')
Url('https://service.io/?q=3fc3645b439ce8e7', scheme='https', host='service.io', tld='io', host_type='domain', path='/', query='q=3fc3645b439ce8e7')
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
import requests

from lnurl import Lnurl, LnurlResponse

lnurl = Lnurl('LNURL1DP68GURN8GHJ7MRWW4EXCTNZD9NHXATW9EU8J730D3H82UNV94MKJARGV3EXZAELWDJHXUMFDAHR6WFHXQERSVPCA649RV')
r = requests.get(lnurl.url)

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
```

If you have already `requests` installed, you can also use the `.handle()` function directly.
It will return the appropriate response for a LNURL.

```python
>>> import lnurl
>>> lnurl.handle('lightning:LNURL1DP68GURN8GHJ7MRWW4EXCTNZD9NHXATW9EU8J730D3H82UNV94CXZ7FLWDJHXUMFDAHR6V33XCUNSVE38QV6UF')
LnurlPayResponse(tag='payRequest', callback=Url('https://lnurl.bigsun.xyz/lnurl-pay/callback/2169831', scheme='https', host='lnurl.bigsun.xyz', tld='xyz', host_type='domain', path='/lnurl-pay/callback/2169831'), min_sendable=3000, max_sendable=6000, metadata=LnurlPayMetadata('[["text/plain","rJcIdiekFE cTLynjPIqzum"]]'))
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

[travis]: https://travis-ci.com/python-ln/lnurl?branch=master
[travis-badge]: https://api.travis-ci.com/python-ln/lnurl.svg?branch=master
[codecov]: https://codecov.io/gh/python-ln/lnurl
[codecov-badge]: https://codecov.io/gh/python-ln/lnurl/branch/master/graph/badge.svg
[pypi]: https://pypi.org/project/lnurl/
[pypi-badge]: https://badge.fury.io/py/lnurl.svg
[pypi-versions]: https://img.shields.io/pypi/pyversions/lnurl.svg
[license-badge]: https://img.shields.io/badge/license-MIT-blue.svg

[lnurl]: https://telegra.ph/lnurl-a-protocol-for-seamless-interaction-between-services-and-Lightning-wallets-08-19
[lnurl-spec]: https://github.com/btcontract/lnurl-rfc/blob/master/spec.md
[pydantic]: https://github.com/samuelcolvin/pydantic/
