"""
Isolated Cryptographic Vault for PII Airlock.
Implements AES-256-GCM encryption for zero-trust raw PII storage,
format-preserving typed token generation, and role-governed detokenization.
"""

import hashlib
import os
from datetime import UTC, datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import BaseModel, Field

from services.config import get_settings


class VaultRecord(BaseModel):
    token: str
    kind: str
    ciphertext: bytes
    nonce: bytes
    scope: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PIIVault:
    def __init__(self, key_hex: str | None = None, salt: str | None = None):
        settings = get_settings()
        raw_key = key_hex or settings.ARGUS_VAULT_ENCRYPTION_KEY
        self.key = bytes.fromhex(raw_key)
        if len(self.key) != 32:
            raise ValueError(f"AES-256 requires a 32-byte key, got {len(self.key)} bytes")

        self.aesgcm = AESGCM(self.key)
        self.salt = salt or settings.ARGUS_TOKENIZER_SALT
        # In-memory storage cache (mirrors argus_vault.tokens in database)
        self._store: dict[str, VaultRecord] = {}

    def _generate_token(self, kind: str, raw_value: str, scope: str) -> str:
        """Generates a deterministic typed token scoped to session/customer."""
        hasher = hashlib.sha256()
        hasher.update(self.salt.encode("utf-8"))
        hasher.update(scope.encode("utf-8"))
        hasher.update(raw_value.encode("utf-8"))
        short_hash = hasher.hexdigest()[:6].upper()
        return f"<{kind.upper()}_{short_hash}>"

    def tokenize_and_store(self, kind: str, raw_value: str, scope: str = "default_session") -> str:
        """Encrypts raw PII with AES-256-GCM and stores in vault, returning the safe token."""
        token = self._generate_token(kind, raw_value, scope)
        if token in self._store:
            return token

        nonce = os.urandom(12)  # 96-bit standard GCM nonce
        plaintext_bytes = raw_value.encode("utf-8")
        # AESGCM encrypt appends 16-byte authentication tag to ciphertext
        ciphertext_with_tag = self.aesgcm.encrypt(nonce, plaintext_bytes, scope.encode("utf-8"))

        record = VaultRecord(
            token=token,
            kind=kind,
            ciphertext=ciphertext_with_tag,
            nonce=nonce,
            scope=scope,
        )
        self._store[token] = record
        return token

    def detokenize(self, token: str, requesting_role: str, scope: str = "default_session") -> str:
        """Detokenizes a token back to raw PII ONLY if the requesting role has clearance."""
        authorized_roles = {"compliance_officer", "authorized_analyst", "system_vault"}
        if requesting_role not in authorized_roles:
            raise PermissionError(f"Role '{requesting_role}' is not authorized to detokenize PII.")

        record = self._store.get(token)
        if not record:
            raise KeyError(f"Token '{token}' not found in PII vault.")

        plaintext_bytes = self.aesgcm.decrypt(
            record.nonce, record.ciphertext, record.scope.encode("utf-8")
        )
        return plaintext_bytes.decode("utf-8")

    def has_token(self, token: str) -> bool:
        return token in self._store

    def count(self) -> int:
        return len(self._store)
