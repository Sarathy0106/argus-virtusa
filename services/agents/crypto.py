"""
Ed25519 Cryptographic Signatures for ARGUS Agent Mesh.
Ensures non-repudiation and cryptographic identity verification across all A2A calls.
"""

import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519


class AgentKeyPair:
    def __init__(self, private_key: ed25519.Ed25519PrivateKey | None = None):
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

    @property
    def public_key_hex(self) -> str:
        raw_bytes = self.public_key.public_bytes_raw()
        return raw_bytes.hex()

    def sign_payload(self, payload: dict[str, Any]) -> str:
        """Signs a canonical JSON serialized payload, returning hex signature."""
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        signature_bytes = self.private_key.sign(serialized.encode("utf-8"))
        return signature_bytes.hex()

    @staticmethod
    def verify_signature(public_key_hex: str, signature_hex: str, payload: dict[str, Any]) -> bool:
        """Verifies an Ed25519 signature against a canonical JSON payload."""
        try:
            pub_bytes = bytes.fromhex(public_key_hex)
            sig_bytes = bytes.fromhex(signature_hex)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
            public_key.verify(sig_bytes, serialized.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError):
            return False
