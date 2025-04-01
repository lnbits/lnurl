from lnurl.helpers import lnurlauth_signature, lnurlauth_verify

# taken from LUD-04 signature check example
domain = "auth.site.com"
k1 = "e2af6254a8df433264fa23f67eb8188635d15ce883e8fc020989d5f82ae6f11e"
key = "02c3b844b8104f0c1b15c507774c9ba7fc609f58f343b9b149122e944dd20c9362"
sig = (
    "304402203767faf494f110b139293d9bab3c50e07b3bf33c463d4aa767256cd09132dc510"
    "2205821f8efacdb5c595b92ada255876d9201e126e2f31a140d44561cc1f7e9e43d"
)


class TestHelpersLnurlauth:

    def test_verify(self):
        assert lnurlauth_verify(k1, key, sig) is True

    def test_verify_invalid(self):
        k1 = "0" * 32
        key = "0" * 33
        sig = "0" * 64
        assert lnurlauth_verify(k1, key, sig) is False

    def test_signature(self):
        _key, _sig = lnurlauth_signature(k1, key, domain)
        assert lnurlauth_verify(k1, _key, _sig) is True
        # invalid signature
        assert lnurlauth_verify(k1, key, _sig) is False
