import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from contracts.common import DecisionOutcome, RiskTier


def canonical_json_hash(data: dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 hash using sorted keys and compact JSON formatting."""
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class DecisionRecord(BaseModel):
    id: str = Field(..., description="Unique decision ID")
    transaction_id: str = Field(..., description="Target transaction ID")
    input_hash: str = Field(..., description="Deterministic hash of all inputs evaluated")
    rule_bundle_ver: str = Field(..., description="OPA policy bundle version applied")
    model_ver: str = Field(..., description="ML model version applied")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Calibrated risk probability")
    outcome: DecisionOutcome = Field(..., description="ALLOW, HOLD, ESCALATE, or BLOCK")
    tier: RiskTier = Field(..., description="T0 (auto), T1 (analyst), T2 (maker-checker), T3 (STR)")
    evidence_ids: list[str] = Field(
        default_factory=list, description="IDs of rules or data triggering outcome"
    )
    output_hash: str = Field(..., description="Deterministic hash of the decision output")
    explanation_summary: str | None = Field(default=None)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        decision_id: str,
        transaction_id: str,
        input_data: dict[str, Any],
        rule_bundle_ver: str,
        model_ver: str,
        risk_score: float,
        outcome: DecisionOutcome,
        tier: RiskTier,
        evidence_ids: list[str],
        explanation_summary: str | None = None,
        recorded_at: datetime | None = None,
    ) -> "DecisionRecord":
        input_h = canonical_json_hash(input_data)
        output_payload = {
            "transaction_id": transaction_id,
            "outcome": outcome.value,
            "tier": tier.value,
            "risk_score": round(risk_score, 4),
            "evidence_ids": sorted(evidence_ids),
            "rule_bundle_ver": rule_bundle_ver,
            "model_ver": model_ver,
        }
        output_h = canonical_json_hash(output_payload)
        return cls(
            id=decision_id,
            transaction_id=transaction_id,
            input_hash=input_h,
            rule_bundle_ver=rule_bundle_ver,
            model_ver=model_ver,
            risk_score=risk_score,
            outcome=outcome,
            tier=tier,
            evidence_ids=evidence_ids,
            output_hash=output_h,
            explanation_summary=explanation_summary,
            recorded_at=recorded_at or datetime.now(UTC),
        )
