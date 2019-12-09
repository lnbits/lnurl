LNURL implementation for Python
===============================

[![travis-badge]][travis]
[![codecov-badge]][codecov]
[![pypi-badge]][pypi]
[![pypi-versions]][pypi]
[![license-badge]](LICENSE)

Basic usage
-----------

```python
>>> import lnurl
>>> lnurl.encode('https://service.io/?q=3fc3645b439ce8e7')
Lnurl('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9', url=HttpsUrl('https://service.io/?q=3fc3645b439ce8e7', scheme='https', host='service.io', tld='io', host_type='domain', path='/', query='q=3fc3645b439ce8e7'))
>>> lnurl.decode('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9')
HttpsUrl('https://service.io/?q=3fc3645b439ce8e7', scheme='https', host='service.io', tld='io', host_type='domain', path='/', query='q=3fc3645b439ce8e7')
```

The `Lnurl` object provides some extra utilities.

```python
from lnurl import Lnurl

lnurl = Lnurl('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9')
lnurl.bech32  # 'LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9'
lnurl.bech32.hrp  # 'lnurl'
lnurl.url  # 'https://service.io/?q=3fc3645b439ce8e7'
lnurl.url.host  #  service.io
lnurl.url.base  # 'https://service.io/'
lnurl.url.query  # 'q=3fc3645b439ce8e7'
lnurl.url.query_params  # {'q': '3fc3645b439ce8e7'}
```

Parsing LNURL responses
-----------------------

You can use a `LnurlResponse` to wrap responses you get from a LNURL.
The different types of responses defined in the LNURL specification have a different response class 
with different properties (see `models.py`):

```python
import lnurl
import requests

from lnurl import LnurlResponse

bech32 = 'LNURL1DP68GURN8GHJ7MRWW4EXCTNZD9NHXATW9EU8J730D3H82UNV94MKJARGV3EXZAELWDJHXUMFDAHR6WFHXQERSVPCA649RV'
lnurl = lnurl.decode(bech32)

r = requests.get(lnurl.url)

res = LnurlResponse.from_dict(res.json())  # LnurlWithdrawResponse
res.max_sats  # int
res.callback.base  # str
res.callback.query_params # dict
```

Or if you have already `requests` installed, you can use the `.handle()` function directly.
It will return the appropriate response for an LNURL.

```python
>>> import lnurl
>>> lnurl.handle('lightning:LNURL1DP68GURN8GHJ7MRWW4EXCTNZD9NHXATW9EU8J730D3H82UNV94MKJARGV3EXZAELWDJHXUMFDAHR6WFHXQERSVPCA649RV')
LnurlWithdrawResponse(tag='withdrawRequest', callback=HttpsUrl('https://lnurl.bigsun.xyz/lnurl-withdraw/callback/9702808', scheme='https', host='lnurl.bigsun.xyz', tld='xyz', host_type='domain', path='/lnurl-withdraw/callback/9702808'), k1='38d304051c1b76dcd8c5ee17ee15ff0ebc02090c0afbc6c98100adfa3f920874', min_withdrawable=551000, max_withdrawable=551000, default_description='sample withdraw')
```

Building your own LNURL responses
---------------------------------

If you are managing a service, you can use the `lnurl` package to build valid responses too.

```python
from lnurl import LnurlWithdrawResponse

res = LnurlWithdrawResponse(**{
    'callback': 'https://lnurl.bigsun.xyz/lnurl-withdraw/callback/9702808',
    'k1': 38d304051c1b76dcd8c5ee17ee15ff0ebc02090c0afbc6c98100adfa3f920874,
    'min_withdrawable': 551000,
    'max_withdrawable': 551000,
    'default_description': 'sample withdraw',
})
res.json()  # str
res.dict()  # dict
```

All responses are `pydantic` models, so the information you provide will be validated and you have
access to `.json()` and `.dict()` methods to export the data.

**When data is exported it will be exported by default using camelCase keys, because the LNURL spec
uses camelCase.** You can also use camelCases when you parse the data, and it will be converted to
snake_case to make your Python code nicer.

If you want to export the data using snake_case (in your Python code, for example), you can change
the `by_alias` parameter: `res.dict(by_alias=False)` (it is `True` by default).

[travis-badge]: https://travis-ci.org/python-ln/lnurl.svg?branch=master
[travis]: https://travis-ci.org/python-ln/lnurl?branch=master
[codecov-badge]: https://codecov.io/gh/python-ln/lnurl/branch/master/graph/badge.svg
[codecov]: https://codecov.io/gh/python-ln/lnurl
[pypi]: https://pypi.org/project/lnurl/
[pypi-badge]: https://badge.fury.io/py/lnurl.svg
[pypi-versions]: https://img.shields.io/pypi/pyversions/lnurl.svg
[license-badge]: https://img.shields.io/badge/license-MIT-blue.svg
