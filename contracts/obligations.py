from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class RegulatoryObligation(BaseModel):
    id: str = Field(..., description="Unique obligation ID (e.g. OBL-RBI-2024-001)")
    clause_id: str = Field(..., description="Foreign key to RegulationClause.id")
    actor: str = Field(
        ..., description="Regulated entity (e.g. RE, Commercial Bank, Payment System Operator)"
    )
    trigger_event: str = Field(
        ..., description="Event triggering rule (e.g. TRANSACTION_SUBMITTED, KYC_UPDATE)"
    )
    condition_json: dict[str, Any] = Field(
        ..., description="Structured machine-readable conditions"
    )
    action_json: dict[str, Any] = Field(
        ..., description="Prescribed action (e.g. {action: 'HOLD', tier: 'T2'})"
    )
    rule_ref: str = Field(
        ..., description="Corresponding OPA rule name (e.g. aml_structuring_window)"
    )
    severity: str = Field(default="HIGH")  # LOW, MEDIUM, HIGH, CRITICAL
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
