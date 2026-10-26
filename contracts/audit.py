import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def compute_audit_hash(
    prev_hash: str,
    payload_hash: str,
    event_type: str,
    entity_id: str,
    signer: str,
    timestamp_iso: str,
) -> str:
    """Computes SHA-256 hash chaining for an audit ledger entry."""
    chain_input = f"{prev_hash}|{payload_hash}|{event_type}|{entity_id}|{signer}|{timestamp_iso}"
    return hashlib.sha256(chain_input.encode("utf-8")).hexdigest()


class AuditEntry(BaseModel):
    seq: int | None = Field(default=None, description="Monotonically increasing sequence number")
    prev_hash: str = Field(
        ..., description="Hash of the preceding audit record (0000... for genesis)"
    )
    payload_hash: str = Field(..., description="SHA-256 hash of the payload")
    event_type: str = Field(
        ..., description="e.g. DECISION_RECORDED, RULE_MODIFIED, MAKER_CHECKER_APPROVAL"
    )
    entity_id: str = Field(
        ..., description="ID of the related entity (decision_id, rule_id, case_id)"
    )
    signer: str = Field(..., description="Signer identity (service ID, analyst ID, or agent ID)")
    signature: str | None = Field(default=None, description="Cryptographic signature (Ed25519 hex)")
    payload: dict[str, Any] = Field(..., description="Full audit payload")
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        prev_hash: str,
        event_type: str,
        entity_id: str,
        signer: str,
        payload: dict[str, Any],
        signature: str | None = None,
        recorded_at: datetime | None = None,
        seq: int | None = None,
    ) -> "AuditEntry":
        ts = recorded_at or datetime.now(timezone.utc)
        payload_serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        payload_hash = hashlib.sha256(payload_serialized.encode("utf-8")).hexdigest()
        return cls(
            seq=seq,
            prev_hash=prev_hash,
            payload_hash=payload_hash,
            event_type=event_type,
            entity_id=entity_id,
            signer=signer,
            signature=signature,
            payload=payload,
            recorded_at=ts,
        )

    def verify_hash(self) -> str:
        """Returns the computed hash of this audit node in the chain."""
        return compute_audit_hash(
            self.prev_hash,
            self.payload_hash,
            self.event_type,
            self.entity_id,
            self.signer,
            self.recorded_at.isoformat(),
        )

    @property
    def entry_hash(self) -> str:
        return self.verify_hash()

