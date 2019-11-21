#!/usr/bin/env python3
import re
import urllib.parse
from bech32 import bech32_encode, bech32_decode, convertbits


# Copyright (c) 2017 Pieter Wuille
# Copyright (c) 2019 jogco
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Simple implementation of LNURL for Python 3.5+"""


class LNURLError(ValueError): pass
class InvalidLNURL(LNURLError): pass
class InvalidHTTPSURL(LNURLError): pass
LNURL_MAXLENGTH = 4096 # arbitrary
CTRL = re.compile(r'[\u0000-\u001f\u007f-\u009f]')
NON_RFC3986 = re.compile(r"[^]a-zA-Z0-9._~:/?#[@!$&'()*+,;=-]")


def decode(data, strict_rfc3986 = False, autocomplete_https = True):
    """Safely decode a LNURL"""

    if len(data) > LNURL_MAXLENGTH:
        raise InvalidLNURL('too long')

    hrp, data_part = bech32_decode(data)
    if None in (hrp, data_part):
        raise InvalidLNURL('invalid bech32')

    if hrp != 'lnurl':
        raise InvalidLNURL('not an LNURL')

    try:
        url = bytes(convertbits(data_part, 5, 8, False)).decode('utf-8')
    except UnicodeDecodeError:
        raise InvalidLNURL('invalid UTF-8 in URL')

    if strict_rfc3986:
        if NON_RFC3986.search(url):
            raise InvalidLNURL('invalid characters in HTTPS URL')
    else:
        # control characters (unicode blocks C0 and C1, plus DEL)
        if CTRL.search(url):
            raise InvalidLNURL('invalid characters in HTTPS URL')

    try:
        u = urllib.parse.urlsplit(url)
    except ValueError:
        raise InvalidLNURL('invalid https URL')

    if autocomplete_https and not u.scheme and not u.netloc:
        url = 'https://' + url

        try:
            u = urllib.parse.urlsplit(url)
        except ValueError:
            raise InvalidLNURL('invalid HTTPS URL')

    if u.scheme.lower() != 'https' or not u.netloc or not u.hostname:
        raise InvalidLNURL('invalid HTTPS URL')

    return url


def encode(https_url):
    """Encode a LNURL"""
    if https_url[0:8].lower() != 'https://':
        raise InvalidHTTPSURL

    try:
        data = bech32_encode('lnurl',
            convertbits(https_url.encode('utf-8'), 8, 5, True))

    except UnicodeEncodeError:
        raise InvalidHTTPSURL

    if len(data) > LNURL_MAXLENGTH:
        raise InvalidHTTPSURL('too long')

    return data.upper()
