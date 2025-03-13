from base64 import b64decode, b64encode

import pytest
from Cryptodome import Random

from lnurl.helpers import aes_decrypt, aes_encrypt


class TestAesEncryption:
    @pytest.mark.parametrize("plaintext", ["dni was here", "short", "A" * 4096])
    def test_encrypt_decrypt(self, plaintext):
        preimage = Random.get_random_bytes(32)
        ciphertext, iv = aes_encrypt(preimage, plaintext)
        assert ciphertext != plaintext
        assert len(b64decode(ciphertext)) % 16 == 0
        assert len(iv) == 24
        assert len(b64decode(iv)) == 16
        assert aes_decrypt(preimage, ciphertext, iv) == plaintext
        with pytest.raises(ValueError):
            assert aes_decrypt(bytes(32), ciphertext, iv) == plaintext
        with pytest.raises(ValueError):
            assert aes_decrypt(preimage, ciphertext, b64encode(bytes(16)).decode()) == plaintext
        with pytest.raises(ValueError):
            assert aes_decrypt(preimage, b64encode(bytes(32)).decode(), iv) == plaintext

    def test_encrypt_empty(self):
        with pytest.raises(ValueError):
            _ = aes_encrypt(b64encode(bytes(32)), "")

    def test_encrypt_fails_too_small_key(self):
        with pytest.raises(ValueError):
            _ = aes_encrypt(b64encode(bytes(33)), "dni was here")

    def test_encrypt_fails_too_big_key(self):
        with pytest.raises(ValueError):
            _ = aes_encrypt(b64encode(bytes(31)), "dni was here")

    # TODO: interesting, why?
    def test_encrypt_fails_for_icons(self):
        icons = "lightning icons: ⚡⚡"
        with pytest.raises(Exception):
            _ = aes_encrypt(b64encode(bytes(32)), icons)
