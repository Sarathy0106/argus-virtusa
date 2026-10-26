"""
Deployment, Shadow Mode, Canary Ramp and Rollback Contracts for ARGUS v2.
Enforces draft-only safety, dual human approval cryptographic tokens,
shadow-mode concordance, canary progression, and sub-minute rollback triggers.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DeploymentStage(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    SHADOW = "SHADOW"
    CANARY_1 = "CANARY_1"
    CANARY_10 = "CANARY_10"
    CANARY_50 = "CANARY_50"
    PROMOTED_100 = "PROMOTED_100"
    ROLLED_BACK = "ROLLED_BACK"


class DualApprovalToken(BaseModel):
    token_id: str = Field(..., description="Unique approval token ID (e.g. TOK-APP-2024-001)")
    rule_name: str
    bundle_version: str
    maker_id: str
    checker_id: str
    maker_signature: str
    checker_signature: str
    approved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    is_valid: bool = True


class ShadowEvaluation(BaseModel):
    rule_name: str
    total_evaluations: int
    live_rule_alerts: int
    shadow_rule_alerts: int
    discrepancy_count: int
    concordance_percentage: float
    backtest_predicted_delta: float
    observed_shadow_delta: float
    drift_from_backtest_pct: float
    within_tolerance: bool
    sample_discrepancies: list[dict[str, Any]] = Field(default_factory=list)


class CanaryMetrics(BaseModel):
    stage: DeploymentStage
    traffic_pct: int = Field(..., description="Traffic percentage (1, 10, 50, 100)")
    evaluations_count: int = 0
    alerts_count: int = 0
    alert_rate_pct: float = 0.0
    decline_rate_pct: float = 0.0
    latency_p95_ms: float = 0.0
    error_rate_pct: float = 0.0
    breach_detected: bool = False
    breach_reason: str | None = None


class RollbackRecord(BaseModel):
    rollback_id: str = Field(..., description="Unique rollback incident ID")
    rule_name: str
    from_version: str
    to_version: str
    reason: str
    triggered_by: str = Field(default="AUTOMATIC_BREACH")  # AUTOMATIC_BREACH, MANUAL
    recovery_time_ms: float = Field(default=0.0, description="Time taken to revert pointer in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
