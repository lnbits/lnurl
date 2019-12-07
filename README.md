LNURL implementation for Python
===============================

[![travis-badge]][travis]
[![codecov-badge]][codecov]
[![pypi-badge]][pypi]
[![license-badge]](LICENSE)

Basic usage
-----------

```python
>>> import lnurl
>>> lnurl.encode('https://service.io/?q=3fc3645b439ce8e7')
>>> lnurl.decode('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9')
```

Advanced usage
--------------

The `Lnurl` object wraps a bech32 LNURL to provide some extra utilities.

```python
import lnurl

lnurl = lnurl.decode('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9')
lnurl.bech32  # 'LNURL1DP68GURN8GHJ7UM9WFMXJCM99E5K7TELWY7NXENRXVMRGDTZXSENJCM98PJNWXQ96S9'
lnurl.url  # 'https://service.io/?q=3fc3645b439ce8e7'
lnurl.url.base  # 'https://service.io/'
lnurl.url.query_params  # {'q': '3fc3645b439ce8e7'}
```

You can also use a `LnurlResponse` to wrap responses you get from a LNURL.  
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
>>> lnurl.handle('LNURL1DP68GURN8GHJ7MRWW4EXCTNZD9NHXATW9EU8J730D3H82UNV94MKJARGV3EXZAELWDJHXUMFDAHR6WFHXQERSVPCA649RV')
LnurlWithdrawResponse(tag='withdrawRequest', callback=HttpsUrl('https://lnurl.bigsun.xyz/lnurl-withdraw/callback/9702808', scheme='https', host='lnurl.bigsun.xyz', tld='xyz', host_type='domain', path='/lnurl-withdraw/callback/9702808'), k1='b7a051db1ac71ae8d3f62727e39d52ae1406f625561b2129c4902b4f37044248', min_withdrawable=923000, max_withdrawable=2769000, default_description='sample withdraw')
```

[travis-badge]: https://travis-ci.org/python-ln/lnurl.svg?branch=master
[travis]: https://travis-ci.org/python-ln/lnurl?branch=master
[codecov-badge]: https://codecov.io/gh/python-ln/lnurl/branch/master/graph/badge.svg
[codecov]: https://codecov.io/gh/python-ln/lnurl
[pypi-badge]: https://badge.fury.io/py/lnurl.svg
[pypi]: https://pypi.org/project/lnurl/
[license-badge]: https://img.shields.io/badge/license-MIT-blue.svg
