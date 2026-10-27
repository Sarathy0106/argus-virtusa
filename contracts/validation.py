"""
Validation and Objection Loop Contracts for ARGUS v2.
Defines the deterministic pass/fail gates and objection payloads that
the Validator Agent issues to re-route execution back to Stage 3 or Stage 4.
"""

from enum import Enum
from pydantic import BaseModel, Field


class ObjectionTargetStage(str, Enum):
    POLICY_MAPPING = "POLICY_MAPPING"
    RULE_AUTHORING = "RULE_AUTHORING"


class ObjectionCode(str, Enum):
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    ACTIVE_CONFLICT_UNRESOLVED = "ACTIVE_CONFLICT_UNRESOLVED"
    UNCITED_CLAUSE = "UNCITED_CLAUSE"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    TEST_FAILURE = "TEST_FAILURE"
    SURGE_THRESHOLD_EXCEEDED = "SURGE_THRESHOLD_EXCEEDED"
    INVALID_THRESHOLD = "INVALID_THRESHOLD"


class ValidationObjection(BaseModel):
    objection_id: str = Field(..., description="Unique objection reference (e.g. OBJ-VAL-001)")
    target_stage: ObjectionTargetStage = Field(
        ..., description="Which stage must resolve this objection (Stage 3 or Stage 4)"
    )
    code: ObjectionCode = Field(..., description="Categorical reason for objection")
    message: str = Field(..., description="Human and agent readable critique of the flaw")
    suggested_fix: str = Field(..., description="Actionable remediation instructions")
    source_clause_id: str | None = Field(default=None)
    counter_example: dict | None = Field(
        default=None,
        description="Z3 counter-example transaction demonstrating the conflict, if any.",
    )


class ValidationReport(BaseModel):
    rule_name: str
    iteration: int = Field(default=1, description="Iteration index in objection loop")
    passed: bool = Field(default=False, description="True only if all deterministic gates pass")
    schema_valid: bool = Field(default=False)
    citation_coverage_pct: float = Field(default=0.0)
    conflict_check_passed: bool = Field(default=False)
    test_suite_passed: bool = Field(default=False)
    tests_total: int = Field(default=0)
    tests_passed: int = Field(default=0)
    objections: list[ValidationObjection] = Field(default_factory=list)
    certificate_id: str | None = Field(default=None, description="Cryptographic certificate if passed")
