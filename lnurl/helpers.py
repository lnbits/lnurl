import hmac
from base64 import b64decode, b64encode
from hashlib import sha256
from typing import List, Optional, Set, Tuple

from bech32 import bech32_decode, bech32_encode, convertbits
from bip32 import BIP32
from Cryptodome import Random
from Cryptodome.Cipher import AES
from ecdsa import SECP256k1, SigningKey, VerifyingKey
from ecdsa.util import sigdecode_der, sigencode_der

from .exceptions import InvalidLnurl, InvalidUrl

LUD13_PHRASE = (
    "DO NOT EVER SIGN THIS TEXT WITH YOUR PRIVATE KEYS! IT IS ONLY USED "
    "FOR DERIVATION OF LNURL-AUTH HASHING-KEY, DISCLOSING ITS SIGNATURE "
    "WILL COMPROMISE YOUR LNURL-AUTH IDENTITY AND MAY LEAD TO LOSS OF FUNDS!"
)


def aes_decrypt(preimage: bytes, ciphertext_base64: str, iv_base64: str) -> str:
    """
    Decrypt a message using AES-CBC. LUD-10
    LUD-10, used in PayRequest success actions.
    """
    if len(preimage) != 32:
        raise ValueError("AES key must be 32 bytes long")
    if len(iv_base64) != 24:
        raise ValueError("IV must be 24 bytes long")
    cipher = AES.new(preimage, AES.MODE_CBC, b64decode(iv_base64))
    decrypted = cipher.decrypt(b64decode(ciphertext_base64))
    size = len(decrypted)
    pad = decrypted[size - 1]
    if (0 > pad > 16) or (pad > 1 and decrypted[size - 2] != pad):
        raise ValueError("Decryption failed. Error with padding.")
    decrypted = decrypted[: size - pad]
    if len(decrypted) == 0:
        raise ValueError("Decryption failed. Empty message.")
    try:
        return decrypted.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Decryption failed. UnicodeDecodeError") from exc


def aes_encrypt(preimage: bytes, message: str) -> tuple[str, str]:
    """
    Encrypt a message using AES-CBC with a random IV.
    LUD-10, used in PayRequest success actions.
    """
    if len(preimage) != 32:
        raise ValueError("AES key must be 32 bytes long")
    if len(message) == 0:
        raise ValueError("Message must not be empty")
    iv = Random.get_random_bytes(16)
    cipher = AES.new(preimage, AES.MODE_CBC, iv)
    pad = 16 - len(message) % 16
    message += chr(pad) * pad
    ciphertext = cipher.encrypt(message.encode("utf-8"))
    return b64encode(ciphertext).decode(), b64encode(iv).decode("utf-8")


# LUD-04: auth base spec.
def lnurlauth_signature(k1: str, linking_key: bytes) -> tuple[str, str]:
    """
    Sign a k1 with a linking_key from (bip32 or signMessage) and a domain.

    Obtain the linking_key from lnurlauth_derive_linking_key or lnurlauth_derive_linking_key_sign_message.
    """
    auth_key = SigningKey.from_string(linking_key, curve=SECP256k1, hashfunc=sha256)
    sig = auth_key.sign_digest_deterministic(bytes.fromhex(k1), sigencode=sigencode_der)
    if not auth_key.verifying_key:
        raise ValueError("LNURLauth verifying_key does not exist")
    key = auth_key.verifying_key.to_string("compressed")
    return key.hex(), sig.hex()


def lnurlauth_verify(k1: str, key: str, sig: str) -> bool:
    """
    Verify a k1 with a key and a signature.
    """
    try:
        verifying_key = VerifyingKey.from_string(bytes.fromhex(key), hashfunc=sha256, curve=SECP256k1)
        verifying_key.verify_digest(bytes.fromhex(sig), bytes.fromhex(k1), sigdecode=sigdecode_der)
        return True
    except Exception as exc:
        print(exc)
        return False


# LUD-05: BIP32-based seed generation for auth protocol.
def lnurlauth_derive_linking_key(seed: str, domain: str) -> tuple[bytes, bytes]:
    """
    Derive a key from a masterkey.
    RETURN (linking_key, linking_key_pub) in hex
    """
    master_key = lnurlauth_master_key_from_seed(seed)
    hashing_key = BIP32.get_privkey_from_path(master_key, "m/138'/0")
    _path_suffix = lnurlauth_derive_path(hashing_key, domain)
    linking_key = BIP32.get_privkey_from_path(master_key, _path_suffix)
    linking_key_pub = BIP32.get_pubkey_from_path(master_key, _path_suffix)
    return linking_key, linking_key_pub


def lnurlauth_master_key_from_seed(seed: str) -> BIP32:
    """
    Derive a masterkey from a seed.
    RETURN (linking_key, linking_key_pub) in hex
    """
    master_key = BIP32.from_seed(bytes.fromhex(seed))
    assert master_key.privkey
    return master_key


def lnurlauth_derive_path(hashing_private_key: bytes, domain_name: str) -> str:
    """
    Derive a path suffix from a hashing_key.

    Take the first 16 bytes of the hash turn it into 4 longs and make a new derivation path with it.
    m/138'/<long1>/<long2>/<long3>/<long4>
    """
    derivation_material = hmac.digest(hashing_private_key, domain_name.encode(), "sha256")
    _path_suffix_longs = [int.from_bytes(derivation_material[i : i + 4], "big") for i in range(0, 16, 4)]
    _path_suffix = "m/138'/" + "/".join(str(i) for i in _path_suffix_longs)
    return _path_suffix


# LUD-13: signMessage-based seed generation for auth protocol.
def lnurlauth_message_to_sign() -> bytes:
    """
    Generate a message to sign for signMessage.
    """
    return sha256(LUD13_PHRASE.encode()).digest()


def lnurlauth_derive_linking_key_sign_message(domain: str, sig: bytes) -> tuple[bytes, bytes]:
    """
    Derive a key from a from signMessage from a node.
    param `sig` is a RFC6979 deterministic signature.
    """
    hashing_key = SigningKey.from_string(sha256(sig).digest(), curve=SECP256k1, hashfunc=sha256)
    linking_key = SigningKey.from_string(
        hmac.digest(hashing_key.to_string(), domain.encode(), "sha256"), curve=SECP256k1, hashfunc=sha256
    )
    assert linking_key.privkey and linking_key.verifying_key
    pubkey = linking_key.verifying_key.to_string("compressed")
    return linking_key.privkey, pubkey


def _bech32_decode(bech32: str, *, allowed_hrp: Optional[Set[str]] = None) -> Tuple[str, List[int]]:
    hrp, data = bech32_decode(bech32)

    if not hrp or not data or (allowed_hrp and hrp not in allowed_hrp):
        raise ValueError(f"Invalid data or Human Readable Prefix (HRP): {hrp}.")

    return hrp, data


def _lnurl_clean(lnurl: str) -> str:
    lnurl = lnurl.strip()
    return lnurl.replace("lightning:", "") if lnurl.startswith("lightning:") else lnurl


def url_decode(lnurl: str) -> str:
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
    except UnicodeDecodeError:
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
    except UnicodeEncodeError:
        raise InvalidUrl

    return lnurl.upper()
