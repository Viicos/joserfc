from typing import Optional, Union, Dict, Type
from functools import cached_property
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey, Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.ed448 import Ed448PublicKey, Ed448PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey, X25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x448 import X448PublicKey, X448PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption,
)
from ..rfc7517.models import CurveKey
from ..rfc7517.types import KeyDict, KeyParameters
from ..rfc7517.pem import CryptographyBinding
from ..util import to_bytes, urlsafe_b64decode, urlsafe_b64encode
from ..registry import KeyParameter

PUBLIC_KEYS_MAP = {
    "Ed25519": Ed25519PublicKey,
    "Ed448": Ed448PublicKey,
    "X25519": X25519PublicKey,
    "X448": X448PublicKey,
}
PRIVATE_KEYS_MAP = {
    "Ed25519": Ed25519PrivateKey,
    "Ed448": Ed448PrivateKey,
    "X25519": X25519PrivateKey,
    "X448": X448PrivateKey,
}
PrivateKeyTypes = (Ed25519PrivateKey, Ed448PrivateKey, X25519PrivateKey, X448PrivateKey)
PublicOKPKey = Union[Ed25519PublicKey, Ed448PublicKey, X25519PublicKey, X448PublicKey]
PrivateOKPKey = Union[Ed25519PrivateKey, Ed448PrivateKey, X25519PrivateKey, X448PrivateKey]


class OKPBinding(CryptographyBinding):
    ssh_type = b"ssh-ed25519"

    @staticmethod
    def import_private_key(obj: KeyDict) -> PrivateOKPKey:
        crv_key: Type[PrivateOKPKey] = PRIVATE_KEYS_MAP[obj["crv"]]  # type: ignore
        d = urlsafe_b64decode(to_bytes(obj["d"]))  # type: ignore
        return crv_key.from_private_bytes(d)

    @staticmethod
    def import_public_key(obj: KeyDict) -> PublicOKPKey:
        crv_key: Type[PublicOKPKey] = PUBLIC_KEYS_MAP[obj["crv"]]  # type: ignore
        x_bytes = urlsafe_b64decode(to_bytes(obj["x"]))  # type: ignore
        return crv_key.from_public_bytes(x_bytes)

    @staticmethod
    def export_private_key(key: PrivateOKPKey) -> Dict[str, str]:
        obj = OKPBinding.export_public_key(key.public_key())
        d_bytes = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        obj["d"] = urlsafe_b64encode(d_bytes).decode("utf-8")
        return obj

    @staticmethod
    def export_public_key(key: PublicOKPKey) -> Dict[str, str]:
        x_bytes = key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        return {
            "crv": get_key_curve(key),
            "x": urlsafe_b64encode(x_bytes).decode("utf-8"),
        }


class OKPKey(CurveKey[PrivateOKPKey, PublicOKPKey]):
    """Key class of the ``OKP`` key type."""

    key_type = "OKP"
    #: Registry definition for OKP Key
    #: https://www.rfc-editor.org/rfc/rfc8037#section-2
    value_registry = {
        "crv": KeyParameter("Curve", "str", private=False, required=True),
        "x": KeyParameter("X Coordinate", "str", private=False, required=True),
        "d": KeyParameter("OKP Private Key", "str", private=True, required=False),
    }
    binding = OKPBinding
    required_fields = frozenset(["crv", "x"])
    private_only_fields = frozenset(["d"])

    def exchange_derive_key(self, key: "OKPKey") -> bytes:
        # used in ECDHESAlgorithm
        pubkey: Union[X25519PublicKey, X448PublicKey] = key.get_op_key("deriveKey")  # type: ignore
        if isinstance(self.private_key, X25519PrivateKey) and isinstance(pubkey, X25519PublicKey):
            return self.private_key.exchange(pubkey)
        elif isinstance(self.private_key, X448PrivateKey) and isinstance(pubkey, X448PublicKey):
            return self.private_key.exchange(pubkey)
        raise ValueError("Invalid key for exchanging shared key")

    @property
    def is_private(self) -> bool:
        return isinstance(self.raw_value, PrivateKeyTypes)

    @cached_property
    def public_key(self) -> PublicOKPKey:
        if isinstance(self.raw_value, PrivateKeyTypes):
            return self.raw_value.public_key()
        return self.raw_value

    @property
    def private_key(self) -> Optional[PrivateOKPKey]:
        if isinstance(self.raw_value, PrivateKeyTypes):
            return self.raw_value
        return None

    @property
    def curve_name(self) -> str:
        return get_key_curve(self.raw_value)

    @classmethod
    def generate_key(
            cls,
            crv: str = "Ed25519",
            parameters: Optional[KeyParameters] = None,
            private: bool = True) -> "OKPKey":
        if crv not in PRIVATE_KEYS_MAP:
            raise ValueError('Invalid crv value: "{}"'.format(crv))

        private_key_cls: Type[PrivateOKPKey] = PRIVATE_KEYS_MAP[crv]  # type: ignore
        raw_key = private_key_cls.generate()
        if private:
            return cls(raw_key, raw_key, parameters)
        pub_key = raw_key.public_key()
        return cls(pub_key, pub_key, parameters)


def get_key_curve(key: Union[PublicOKPKey, PrivateOKPKey]):
    if isinstance(key, (Ed25519PublicKey, Ed25519PrivateKey)):
        return "Ed25519"
    elif isinstance(key, (Ed448PublicKey, Ed448PrivateKey)):
        return "Ed448"
    elif isinstance(key, (X25519PublicKey, X25519PrivateKey)):
        return "X25519"
    elif isinstance(key, (X448PublicKey, X448PrivateKey)):
        return "X448"
    raise ValueError("Invalid key")  # pragma: no cover
