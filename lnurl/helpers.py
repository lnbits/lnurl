import hashlib
import hmac
from io import BytesIO
from typing import List, Optional, Set, Tuple

from bech32 import bech32_decode, bech32_encode, convertbits
from ecdsa import SECP256k1, SigningKey

from .exceptions import InvalidLnurl, InvalidUrl


def lnurlauth_signature(domain: str, secret: str, k1: str) -> tuple[str, str]:
    hashing_key = hashlib.sha256(secret.encode()).digest()
    linking_key = hmac.digest(hashing_key, domain.encode(), "sha256")
    auth_key = SigningKey.from_string(linking_key, curve=SECP256k1, hashfunc=hashlib.sha256)
    sig = auth_key.sign_digest_deterministic(bytes.fromhex(k1), sigencode=encode_strict_der)
    assert auth_key.verifying_key, "LNURLauth verifying_key does not exist"
    key = auth_key.verifying_key.to_string("compressed")
    return key.hex(), sig.hex()


def _bech32_decode(bech32: str, *, allowed_hrp: Optional[Set[str]] = None) -> Tuple[str, List[int]]:
    hrp, data = bech32_decode(bech32)

    if not hrp or not data or (allowed_hrp and hrp not in allowed_hrp):
        raise ValueError(f"Invalid data or Human Readable Prefix (HRP): {hrp}.")

    return hrp, data


def _lnurl_clean(lnurl: str) -> str:
    lnurl = lnurl.strip()
    return lnurl.replace("lightning:", "") if lnurl.startswith("lightning:") else lnurl


def lnurl_decode(lnurl: str) -> str:
    """
    Decode a LNURL and return a url string without performing any validation on it.
    Use `lnurl.decode()` for validation and to get `Url` object.
    """
    _, data = _bech32_decode(_lnurl_clean(lnurl), allowed_hrp={"lnurl"})

    try:
        bech32_data = convertbits(data, 5, 8, False)
        assert bech32_data
        url = bytes(bech32_data).decode("utf-8")
        return url
    except UnicodeDecodeError:  # pragma: nocover
        raise InvalidLnurl


def url_encode(url: str) -> str:
    """
    Encode a URL without validating it first and return a bech32 LNURL string.
    Use `lnurl.encode()` for validation and to get a `Lnurl` object.
    """
    try:
        bech32_data = convertbits(url.encode("utf-8"), 8, 5, True)
        assert bech32_data
        lnurl = bech32_encode("lnurl", bech32_data)
    except UnicodeEncodeError:  # pragma: nocover
        raise InvalidUrl

    return lnurl.upper()


def _int_to_bytes_suitable_der(x: int) -> bytes:
    """for strict DER we need to encode the integer with some quirks"""
    b = x.to_bytes((x.bit_length() + 7) // 8, "big")

    if len(b) == 0:
        # ensure there's at least one byte when the int is zero
        return bytes([0])

    if b[0] & 0x80 != 0:
        # ensure it doesn't start with a 0x80 and so it isn't
        # interpreted as a negative number
        return bytes([0]) + b

    return b


def encode_strict_der(r: int, s: int, order: int):
    # if s > order/2 verification will fail sometimes
    # so we must fix it here see:
    # https://github.com/indutny/elliptic/blob/e71b2d9359c5fe9437fbf46f1f05096de447de57/lib/elliptic/ec/index.js#L146-L147
    if s > order // 2:
        s = order - s

    # now we do the strict DER encoding copied from
    # https://github.com/KiriKiri/bip66 (without any checks)
    r_temp = _int_to_bytes_suitable_der(r)
    s_temp = _int_to_bytes_suitable_der(s)

    r_len = len(r_temp)
    s_len = len(s_temp)
    sign_len = 6 + r_len + s_len

    signature = BytesIO()
    signature.write(0x30.to_bytes(1, "big", signed=False))
    signature.write((sign_len - 2).to_bytes(1, "big", signed=False))
    signature.write(0x02.to_bytes(1, "big", signed=False))
    signature.write(r_len.to_bytes(1, "big", signed=False))
    signature.write(r_temp)
    signature.write(0x02.to_bytes(1, "big", signed=False))
    signature.write(s_len.to_bytes(1, "big", signed=False))
    signature.write(s_temp)

    return signature.getvalue()
