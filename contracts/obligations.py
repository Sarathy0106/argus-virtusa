from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ApplicabilityStatus(str, Enum):
    PENDING = "PENDING"
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONDITIONAL = "CONDITIONAL"


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
    circular_id: str | None = Field(default=None, description="Source circular reference ID")
    deadline: str | None = Field(default=None, description="Regulatory compliance deadline")
    applicability_status: ApplicabilityStatus = Field(
        default=ApplicabilityStatus.PENDING,
        description="Applicability verdict for target bank profile",
    )
    applicability_rationale: str | None = Field(
        default=None, description="Explanation for applicability verdict"
    )
    target_products: list[str] = Field(
        default_factory=list, description="Products impacted (e.g. UPI, RTGS)"
    )
    citations: list[str] = Field(
        default_factory=list, description="Direct clause citations e.g. [CLAUSE:RBI-2024-C01]"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
