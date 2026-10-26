"""
Append-Only Cryptographic Hash-Chained Audit Ledger for ARGUS.
Guarantees immutability and complete forensic traceability.
Hash_n = SHA-256(Hash_{n-1} | payload_hash | event_type | entity_id | signer | timestamp)
"""

from typing import Any

from contracts.audit import AuditEntry

GENESIS_HASH = "0" * 64


class AuditChainIntegrityError(Exception):
    """Raised when any node in the audit chain has been tampered with or broken."""

    pass


class AuditLedger:
    def __init__(self):
        self._chain: list[AuditEntry] = []
        self._current_hash: str = GENESIS_HASH

    def append(
        self,
        event_type: str,
        entity_id: str,
        signer: str,
        payload: dict[str, Any],
        signature: str | None = None,
    ) -> AuditEntry:
        """Appends a new event payload to the cryptographic ledger chain."""
        seq = len(self._chain) + 1
        entry = AuditEntry.create(
            seq=seq,
            prev_hash=self._current_hash,
            event_type=event_type,
            entity_id=entity_id,
            signer=signer,
            payload=payload,
            signature=signature,
        )
        computed_hash = entry.verify_hash()
        self._chain.append(entry)
        self._current_hash = computed_hash
        return entry

    def verify_integrity(self) -> bool:
        """
        Validates the entire ledger from genesis to head.
        Raises AuditChainIntegrityError if any payload or pointer is altered.
        """
        if not self._chain:
            return True

        expected_prev_hash = GENESIS_HASH
        for i, entry in enumerate(self._chain):
            if entry.prev_hash != expected_prev_hash:
                raise AuditChainIntegrityError(
                    f"Chain broken at sequence {entry.seq}: expected prev_hash {expected_prev_hash}, got {entry.prev_hash}"
                )
            expected_prev_hash = entry.verify_hash()

        return True

    def verify_chain(self) -> bool:
        """Alias for verify_integrity."""
        return self.verify_integrity()


    def get_by_seq(self, seq: int) -> AuditEntry | None:
        if 1 <= seq <= len(self._chain):
            return self._chain[seq - 1]
        return None

    def get_latest_hash(self) -> str:
        return self._current_hash

    def count(self) -> int:
        return len(self._chain)
