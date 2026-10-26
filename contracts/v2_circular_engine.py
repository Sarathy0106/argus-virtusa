"""
ARGUS v2 — Data Contracts for Regulatory Circular to Live Rule Engine.
Aligned to FDS NA Use Case 2: Circular In, Safe Rule Out across 10 stages.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class LicenseType(str, Enum):
    SCHEDULED_COMMERCIAL_BANK = "SCHEDULED_COMMERCIAL_BANK"
    PAYMENT_BANK = "PAYMENT_BANK"
    SMALL_FINANCE_BANK = "SMALL_FINANCE_BANK"
    NBFC = "NBFC"
    FOREIGN_BRANCH = "FOREIGN_BRANCH"


class BankProfile(BaseModel):
    id: str = Field(..., description="Bank profile identifier (e.g. BANK-HDFC-01)")
    name: str = Field(..., description="Legal institution name")
    license_type: LicenseType
    has_ad_cat1_forex: bool = Field(default=True, description="Authorized Dealer Cat 1 forex license")
    licensed_products: list[str] = Field(
        default_factory=lambda: ["UPI", "RTGS", "NEFT", "CROSS_BORDER_WIRE", "CREDIT_CARDS", "FOREX", "DIGITAL_LENDING"]
    )
    jurisdictions: list[str] = Field(default_factory=lambda: ["IN", "GLOBAL"])
    tier: str = Field(default="TIER_1_DSIB", description="Domestic Systemically Important Bank tier")


class CircularClause(BaseModel):
    id: str = Field(..., description="Clause ref (e.g. RBI-WIRE-C12A)")
    clause_ref: str
    title: str
    clause_text: str
    valid_from: datetime
    valid_to: datetime
    keywords: list[str] = Field(default_factory=list)


class CircularDocument(BaseModel):
    id: str = Field(..., description="Circular identifier (e.g. RBI/2026/04/MD-WIRE)")
    title: str
    authority: str = Field(default="RBI")  # RBI, FATF, FinCEN, EBA
    published_date: datetime
    effective_date: datetime
    status: str = Field(default="IN_FORCE")
    raw_hash: str
    clauses: list[CircularClause] = Field(default_factory=list)


class ApplicabilityVerdict(BaseModel):
    obligation_id: str
    bank_profile_id: str
    is_applicable: bool
    verdict: str  # APPLICABLE, NOT_APPLICABLE, CONDITIONAL
    matched_products: list[str] = Field(default_factory=list)
    reason: str
    statutory_deadline: str | None = None


class MappingType(str, Enum):
    GAP = "GAP"              # Obligation not covered by existing rules
    OVERLAP = "OVERLAP"      # Partially covered by existing rules
    CONFLICT = "CONFLICT"    # Conflicts with existing policy or rule threshold
    ALIGNED = "ALIGNED"      # Fully covered and aligned


class PolicyMapping(BaseModel):
    obligation_id: str
    clause_ref: str
    internal_policy_id: str
    internal_policy_title: str
    existing_rule_ref: str | None = None
    existing_threshold: float | None = None
    proposed_threshold: float | None = None
    mapping_type: MappingType
    conflict_detail: str | None = None
    suggested_action: str


class RuleLifecycleState(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    SHADOW = "SHADOW"
    CANARY_10 = "CANARY_10"
    CANARY_50 = "CANARY_50"
    CANARY_100 = "CANARY_100"
    ROLLED_BACK = "ROLLED_BACK"


class RuleDSL(BaseModel):
    rule_id: str
    name: str
    version: str = Field(default="1.0.0")
    lifecycle_state: RuleLifecycleState = Field(default=RuleLifecycleState.DRAFT)
    source_clause_id: str
    obligation_id: str
    author: str = Field(default="RuleAuthorAgent")
    dsl_yaml: str
    rego_code: str
    test_code: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BacktestReport(BaseModel):
    rule_id: str
    baseline_rule_id: str
    total_transactions_analyzed: int
    baseline_alert_count: int
    candidate_alert_count: int
    alert_increase_count: int
    delta_percentage: float
    total_flagged_volume_inr: float
    affected_customer_segments: list[dict[str, Any]] = Field(default_factory=list)
    estimated_ops_hours_per_month: float
    false_positive_estimate_pct: float
    sandbox_run_id: str


class ValidationReport(BaseModel):
    rule_id: str
    passed: bool
    schema_ok: bool
    clause_coverage_ok: bool
    citation_grounded: bool
    no_conflict_ok: bool
    objections: list[str] = Field(default_factory=list)
    re_route_stage: str | None = None  # STAGE_3_POLICY_MAPPING or STAGE_4_RULE_AUTHORING
    iteration_count: int = 1
    max_iterations: int = 3


class ApprovalRecord(BaseModel):
    rule_id: str
    bundle_version: str
    maker: str
    checker: str
    maker_signed_at: datetime
    checker_signed_at: datetime
    approval_status: str  # APPROVED, REJECTED
    ed25519_signature: str
    audit_block_seq: int
    ledger_hash: str


class RolloutTelemetry(BaseModel):
    rule_id: str
    current_state: RuleLifecycleState
    canary_percentage: int  # 0 for shadow, 10, 50, 100
    shadow_traffic_count: int = 0
    divergence_count: int = 0
    divergence_rate_pct: float = 0.0
    p95_eval_latency_ms: float = 4.2
    auto_rollback_threshold_divergence_pct: float = 5.0
    is_rolled_back: bool = False
    rollback_reason: str | None = None
    rolled_back_at: datetime | None = None
    active_bundle_tag: str = "v1.0.0"
