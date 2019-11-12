#!/usr/bin/env python3
import re
import urllib.parse

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


CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def bech32_polymod(values):
    """Internal function that computes the Bech32 checksum."""
    generator = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ value
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk


def bech32_hrp_expand(hrp):
    """Expand the HRP into values for checksum computation."""
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def bech32_verify_checksum(hrp, data):
    """Verify a checksum given HRP and converted data characters."""
    return bech32_polymod(bech32_hrp_expand(hrp) + data) == 1


def bech32_create_checksum(hrp, data):
    """Compute the checksum values given HRP and data."""
    values = bech32_hrp_expand(hrp) + data
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def bech32_encode(hrp, data):
    """Compute a Bech32 string given HRP and data values."""
    combined = data + bech32_create_checksum(hrp, data)
    return hrp + "1" + "".join([CHARSET[d] for d in combined])


def bech32_decode(bech):
    """Validate a Bech32 string, and determine HRP and data."""
    if (any(ord(x) < 33 or ord(x) > 126 for x in bech)) or (
        bech.lower() != bech and bech.upper() != bech
    ):
        return (None, None)
    bech = bech.lower()
    pos = bech.rfind("1")
    if pos < 1 or pos + 7 > len(bech):  # or len(bech) > 90:
        return (None, None)
    if not all(x in CHARSET for x in bech[pos + 1 :]):
        return (None, None)
    hrp = bech[:pos]
    data = [CHARSET.find(x) for x in bech[pos + 1 :]]
    if not bech32_verify_checksum(hrp, data):
        return (None, None)
    return (hrp, data[:-6])


def convertbits(data, frombits, tobits, pad=True):
    """General power-of-2 base conversion."""
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


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
