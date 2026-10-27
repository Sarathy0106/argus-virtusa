"""
Declarative Rule DSL and Test Case Contracts for ARGUS v2.
Defines the YAML-authorable Rule DSL specifications, condition AST,
actions, and synthetic unit test cases with clause-level traceability.
"""

from enum import Enum
from typing import Any
import yaml
from pydantic import BaseModel, Field


class DSLOperator(str, Enum):
    GTE = "GTE"
    LTE = "LTE"
    EQ = "EQ"
    NEQ = "NEQ"
    IN = "IN"
    NOT_IN = "NOT_IN"


class DSLCondition(BaseModel):
    field: str = Field(..., description="Target attribute (e.g. input.amount, input.channel)")
    operator: DSLOperator = Field(default=DSLOperator.GTE)
    value: Any = Field(..., description="Literal value or list of values")
    description: str | None = Field(default=None)


class DSLAction(BaseModel):
    outcome: str = Field(default="HOLD", description="HOLD, BLOCK, STEP_UP_AUTH, ALLOW")
    tier: str = Field(default="T1", description="Risk tier T0, T1, T2, T3")
    evidence_id: str = Field(..., description="Mandatory evidence citation tag e.g. [CLAUSE:RBI-2024-C01]")
    cooling_period_hours: int | None = Field(default=None, description="Enforced cooling window")


class DSLTestCase(BaseModel):
    test_id: str = Field(..., description="Unique test case identifier")
    description: str = Field(..., description="Intent of test case")
    input_data: dict[str, Any] = Field(..., description="Input payload to feed to rule")
    expected_hit: bool = Field(default=True, description="Whether rule_hit should evaluate true")
    expected_outcome: str | None = Field(default="HOLD")


class RuleDefinition(BaseModel):
    rule_name: str = Field(..., description="Canonical rule slug e.g. upi_cooling_period_high_value")
    version: str = Field(default="1.0.0", description="Semantic rule version")
    package_path: str = Field(default="argus.compiled", description="Target Rego package")
    clause_id: str = Field(..., description="Traceability link to circular clause")
    obligation_id: str = Field(..., description="Traceability link to regulatory obligation")
    policy_id: str | None = Field(default=None, description="Traceability link to internal policy")
    citations: list[str] = Field(default_factory=list, description="Citations required e.g. [CLAUSE:RBI-WIRE-01]")
    description: str = Field(..., description="Human-readable rule rationale")
    conditions: list[DSLCondition] = Field(default_factory=list)
    action: DSLAction
    test_cases: list[DSLTestCase] = Field(default_factory=list)
    draft_status: str = Field(default="DRAFT_ONLY", description="DRAFT_ONLY until dual approved")
    supersedes: list[str] = Field(
        default_factory=list,
        description="Live rule IDs this draft resolves/supersedes (set once the "
        "objection-loop conflict is resolved). Empty on the naive first draft.",
    )
    conflict_resolved: bool = Field(
        default=False,
        description="True once the author has applied the mapping's conflict "
        "resolution. The naive first draft leaves this False.",
    )

    def to_yaml(self) -> str:
        return yaml.dump(self.model_dump(), sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "RuleDefinition":
        data = yaml.safe_load(yaml_str)
        return cls(**data)
