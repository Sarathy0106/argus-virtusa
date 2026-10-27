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


from datetime import datetime, timezone


class AuditLedger:
    # Injected deterministic clock base. Replay hashes content only and exclude
    # wall-clock fields, so the exact base does not affect replay identity; it is
    # injectable (B11) rather than a hardcoded demo date buried in the code.
    DEFAULT_CLOCK_BASE = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def __init__(
        self,
        deterministic: bool = True,
        clock_base: datetime | None = None,
    ):
        self._chain: list[AuditEntry] = []
        self._current_hash: str = GENESIS_HASH
        self.deterministic = deterministic
        self._clock_base = clock_base or self.DEFAULT_CLOCK_BASE

    def append(
        self,
        event_type: str,
        entity_id: str,
        signer: str,
        payload: dict[str, Any],
        signature: str | None = None,
        recorded_at: Any = None,
    ) -> AuditEntry:
        """Appends a new event payload to the cryptographic ledger chain."""
        seq = len(self._chain) + 1
        if recorded_at is None and self.deterministic:
            from datetime import timedelta

            recorded_at = self._clock_base + timedelta(seconds=seq)

        # Standardize payload timestamp if present and deterministic
        if self.deterministic and isinstance(payload, dict) and "timestamp" in payload:
            clean_payload = dict(payload)
            clean_payload["timestamp"] = recorded_at.isoformat()
        else:
            clean_payload = payload

        entry = AuditEntry.create(
            seq=seq,
            prev_hash=self._current_hash,
            event_type=event_type,
            entity_id=entity_id,
            signer=signer,
            payload=clean_payload,
            signature=signature,
            recorded_at=recorded_at,
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


    # ------------------------------------------------------------------
    # Merkle tree over entry hashes (B11)
    # ------------------------------------------------------------------
    def _leaf_hashes(self) -> list[str]:
        return [e.verify_hash() for e in self._chain]

    @staticmethod
    def _hash_pair(a: str, b: str) -> str:
        import hashlib

        return hashlib.sha256(f"{a}{b}".encode()).hexdigest()

    def merkle_root(self) -> str:
        """SHA-256 Merkle root over all entry hashes. Deterministic; empty chain
        returns the genesis hash."""
        level = self._leaf_hashes()
        if not level:
            return GENESIS_HASH
        while len(level) > 1:
            if len(level) % 2 == 1:
                level.append(level[-1])  # duplicate last for odd counts
            level = [self._hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        return level[0]

    def inclusion_proof(self, index: int) -> dict[str, Any]:
        """Return a Merkle inclusion proof for the entry at 1-based `index`:
        the leaf hash and the sibling hashes needed to recompute the root."""
        leaves = self._leaf_hashes()
        if not (1 <= index <= len(leaves)):
            raise IndexError(f"index {index} out of range (1..{len(leaves)})")
        pos = index - 1
        siblings: list[dict[str, str]] = []
        level = list(leaves)
        leaf = level[pos]
        while len(level) > 1:
            if len(level) % 2 == 1:
                level.append(level[-1])
            sib = pos ^ 1
            siblings.append({"hash": level[sib], "side": "right" if sib > pos else "left"})
            level = [self._hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
            pos //= 2
        return {
            "index": index,
            "leaf_hash": leaf,
            "siblings": siblings,
            "merkle_root": self.merkle_root(),
        }

    @staticmethod
    def verify_inclusion_proof(proof: dict[str, Any]) -> bool:
        """Recompute the root from a leaf + siblings and compare to the claimed
        root."""
        import hashlib

        h = proof["leaf_hash"]
        for sib in proof["siblings"]:
            if sib["side"] == "left":
                h = hashlib.sha256(f"{sib['hash']}{h}".encode()).hexdigest()
            else:
                h = hashlib.sha256(f"{h}{sib['hash']}".encode()).hexdigest()
        return h == proof["merkle_root"]

    def snapshot(self) -> list[AuditEntry]:
        """Deep copy of the chain for tamper demos on a COPY (never the live chain)."""
        return [e.model_copy(deep=True) for e in self._chain]

    def get_by_seq(self, seq: int) -> AuditEntry | None:
        if 1 <= seq <= len(self._chain):
            return self._chain[seq - 1]
        return None

    def get_latest_hash(self) -> str:
        return self._current_hash

    def count(self) -> int:
        return len(self._chain)
