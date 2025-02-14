from unittest import TestCase
from joserfc.jwk import JWKRegistry, guess_key
from joserfc.jwk import OctKey, RSAKey
from joserfc.errors import (
    UnsupportedKeyAlgorithmError,
    UnsupportedKeyUseError,
    UnsupportedKeyOperationError,
)


class Guest:
    def __init__(self):
        self._headers = {}

    def headers(self):
        return self._headers

    def set_kid(self, kid):
        self._headers["kid"] = kid


class TestKeyMethods(TestCase):
    def test_guess_str_key(self):
        key = guess_key("key", Guest())
        self.assertIsInstance(key, OctKey)

    def test_guess_bytes_key(self):
        key = guess_key(b"key", Guest())
        self.assertIsInstance(key, OctKey)

    def test_guess_callable_key(self):
        def key_func(obj):
            return OctKey.import_key("key")

        key = guess_key(key_func, Guest())
        self.assertIsInstance(key, OctKey)

    def test_invalid_key(self):
        self.assertRaises(ValueError, guess_key, {}, Guest())

    def test_import_key(self):
        # test bytes
        key = JWKRegistry.import_key(b"secret", "oct")
        self.assertIsInstance(key, OctKey)

        # test string
        key = JWKRegistry.import_key("secret", "oct")
        self.assertIsInstance(key, OctKey)

        # test dict
        data = key.as_dict()
        key = JWKRegistry.import_key(data)
        self.assertIsInstance(key, OctKey)

        self.assertRaises(ValueError, JWKRegistry.import_key, "secret", "invalid")

    def test_generate_key(self):
        key = JWKRegistry.generate_key("oct", 8)
        self.assertIsInstance(key, OctKey)
        self.assertRaises(ValueError, JWKRegistry.generate_key, "invalid", 8)

    def test_check_use(self):
        key = OctKey.import_key("secret", {"use": "sig"})
        key.check_use("sig")
        self.assertRaises(
            UnsupportedKeyUseError,
            key.check_use,
            "enc"
        )
        self.assertRaises(
            UnsupportedKeyUseError,
            key.check_use,
            "invalid"
        )

    def test_check_alg(self):
        key = OctKey.import_key("secret", {"alg": "HS256"})
        key.check_alg("HS256")
        self.assertRaises(
            UnsupportedKeyAlgorithmError,
            key.check_alg,
            "RS256"
        )

    def test_check_ops(self):
        key = OctKey.import_key("secret", {"key_ops": ["sign", "verify"]})
        key.check_key_op("sign")
        self.assertRaises(
            UnsupportedKeyOperationError,
            key.check_key_op,
            "wrapKey"
        )
        self.assertRaises(
            UnsupportedKeyOperationError,
            key.check_key_op,
            "invalid"
        )
        key = RSAKey.generate_key(private=False)
        self.assertRaises(
            UnsupportedKeyOperationError,
            key.check_key_op,
            "sign"
        )

    def test_import_without_kty(self):
        self.assertRaises(ValueError, JWKRegistry.import_key, {})
