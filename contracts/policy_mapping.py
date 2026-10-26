"""
Policy Mapping, Gap Analysis and Conflict Detection Contracts for ARGUS v2.
Maps extracted obligations against internal bank policies and existing system rules.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ConflictType(str, Enum):
    GAP = "GAP"              # Obligation has no corresponding policy or system rule
    OVERLAP = "OVERLAP"      # Existing rule covers part of the condition but needs tuning
    CONFLICT = "CONFLICT"    # Existing rule actively contradicts new regulatory requirement
    ALIGNED = "ALIGNED"      # Fully compliant with existing policy and rules


class ConflictStatus(str, Enum):
    DETECTED = "DETECTED"
    RESOLVED = "RESOLVED"
    ACCEPTED_RISK = "ACCEPTED_RISK"


class PolicyMappingItem(BaseModel):
    mapping_id: str = Field(..., description="Unique mapping identifier (e.g. MAP-001)")
    obligation_id: str = Field(..., description="ID of the regulatory obligation")
    clause_id: str = Field(..., description="Source circular clause ID")
    internal_policy_id: str | None = Field(
        default=None, description="Existing internal policy reference (e.g. POL-PAY-2023-04)"
    )
    existing_rule_ref: str | None = Field(
        default=None, description="Existing live OPA rule (e.g. upi_single_txn_limit)"
    )
    conflict_type: ConflictType = Field(default=ConflictType.GAP)
    description: str = Field(..., description="Explanation of gap, overlap or conflict")
    suggested_resolution: str = Field(
        ..., description="Recommended action (e.g. Author new rule, modify threshold, supersede rule)"
    )
    status: ConflictStatus = Field(default=ConflictStatus.DETECTED)
    details: dict[str, Any] = Field(default_factory=dict)


class PolicyMappingResult(BaseModel):
    circular_id: str
    bank_id: str
    mappings: list[PolicyMappingItem] = Field(default_factory=list)
    has_conflicts: bool = False
    unresolved_gaps: int = 0
    unresolved_conflicts: int = 0

    def compute_summary(self) -> None:
        self.unresolved_gaps = sum(
            1 for m in self.mappings if m.conflict_type == ConflictType.GAP and m.status == ConflictStatus.DETECTED
        )
        self.unresolved_conflicts = sum(
            1 for m in self.mappings if m.conflict_type == ConflictType.CONFLICT and m.status == ConflictStatus.DETECTED
        )
        self.has_conflicts = self.unresolved_conflicts > 0
