LNURL implementation for Python
===============================

[![travis-badge]][travis]
[![codecov-badge]][codecov]
[![pypi-badge]][pypi]
[![license-badge]](LICENSE)

Basic usage
-----------

```python
import lnurl

lnurl.encode('https://example.com/c?p=a8dw93x2h39s1f')
lnurl.decode('LNURL1DP68GURN8GHJ7ETCV9KHQMR99E3K7MF0VVLHQ0TP8PJ8WWFN0QEXSVEEWVCKVF3A4RP')
```

Advanced usage
--------------

The `Lnurl` object wraps a bech32 LNURL to provide some extra utilities.

```python
from lnurl import Lnurl

lnurl = Lnurl('LNURL1DP68GURN8GHJ7ETCV9KHQMR99E3K7MF0VVLHQ0TP8PJ8WWFN0QEXSVEEWVCKVF3A4RP')
lnurl.bech32  # 'LNURL1DP68GURN8GHJ7ETCV9KHQMR99E3K7MF0VVLHQ0TP8PJ8WWFN0QEXSVEEWVCKVF3A4RP'
lnurl.decoded  # 'https://example.com/c?p=a8dw93x2h39s1f'
lnurl.url.base  # 'https://example.com/c'
lnurl.url.query_params  # {'p': 'a8dw93x2h39s1f'}
```

You can also use a `LnurlResponse` to wrap responses you get from a LNURL.  
The different types of responses defined in the LNURL specification have a different response class 
with different properties (see `models.py`):

```python
import requests

from lnurl import Lnurl, LnurlResponse

lnurl = Lnurl('LNURL1DP68GURN8GHJ7UM9WFMXJCM99E3K7MF0V9CXJ0M384EKZAR0WD5XJ0JELRS')
res = requests.get(lnurl.decoded)
withdraw = LnurlResponse.from_dict(res.json())
withdraw.max_sats  # int
withdraw.callback.base  # str
withdraw.callback.query_params # dict
```

[travis-badge]: https://travis-ci.org/python-ln/lnurl.svg?branch=master
[travis]: https://travis-ci.org/python-ln/lnurl?branch=master
[codecov-badge]: https://codecov.io/gh/python-ln/lnurl/branch/master/graph/badge.svg
[codecov]: https://codecov.io/gh/python-ln/lnurl
[pypi-badge]: https://badge.fury.io/py/lnurl.svg
[pypi]: https://pypi.org/project/lnurl/
[license-badge]: https://img.shields.io/badge/license-MIT-blue.svg
