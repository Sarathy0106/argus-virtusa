"""
Policy Mapper Agent for ARGUS v2 (Stage 3).
Maps extracted obligations against the bank's internal policy catalog
and existing live OPA rules. Identifies Gaps, Overlaps, and Conflicts.
"""

from typing import Any

from contracts.agents import AgentCard, AgentSkill
from contracts.obligations import RegulatoryObligation
from contracts.policy_mapping import (
    ConflictStatus,
    ConflictType,
    PolicyMappingItem,
    PolicyMappingResult,
)
from services.agents.crypto import AgentKeyPair


class PolicyMapperAgent:
    def __init__(self, key_pair: AgentKeyPair | None = None):
        self.key_pair = key_pair or AgentKeyPair()
        self.agent_id = "agent.policy_mapper"
        self.card = AgentCard(
            agent_id=self.agent_id,
            name="Policy & Rule Mapping Agent",
            version="2.0.0",
            public_key=self.key_pair.public_key_hex,
            skills=[
                AgentSkill(
                    name="policy.map_and_detect_conflicts",
                    description="Maps obligations to internal policies and detects rule conflicts/gaps.",
                )
            ],
        )

        # Baseline knowledge of existing live rules and bank policies
        self.existing_rules = {
            "upi_daily_limit": {
                "channel": "UPI",
                "threshold_amount": 100000.0,
                "cooling_period_hours": 0,
                "action": "ALLOW_BELOW_THRESHOLD",
                "policy_ref": "POL-PAY-2023-01",
                "policy_title": "UPI Instant Clearing & Settlement Policy",
            },
            "aml_structuring_window": {
                "channel": "ALL",
                "window_hours": 24,
                "threshold_amount": 50000.0,
                "action": "HOLD",
                "policy_ref": "POL-AML-2022-09",
                "policy_title": "AML Rapid Velocity and Structuring Policy",
            },
        }

    def map_obligations(
        self,
        obligations: list[RegulatoryObligation],
        bank_id: str = "APEX_IN_001",
    ) -> PolicyMappingResult:
        """
        Stage 3: Maps each applicable obligation against existing policies and rules.
        Identifies gaps (missing rules), overlaps, and conflicts.
        """
        mappings: list[PolicyMappingItem] = []
        circular_id = obligations[0].circular_id if obligations else "UNKNOWN_CIRCULAR"

        for idx, obl in enumerate(obligations, 1):
            mapping = self._evaluate_obligation_mapping(obl, idx)
            mappings.append(mapping)

        result = PolicyMappingResult(
            circular_id=circular_id or "CIRCULAR-UNKNOWN",
            bank_id=bank_id,
            mappings=mappings,
        )
        result.compute_summary()
        return result

    def _evaluate_obligation_mapping(
        self, obl: RegulatoryObligation, index: int
    ) -> PolicyMappingItem:
        req_channel = obl.condition_json.get("channel", "UNKNOWN")
        req_threshold = float(obl.condition_json.get("threshold_amount", 0.0))
        req_cooling = obl.condition_json.get("cooling_period_hours", 0)

        # Check for conflict with existing UPI rule
        if req_channel == "UPI" and "upi_daily_limit" in self.existing_rules:
            existing = self.existing_rules["upi_daily_limit"]
            curr_threshold = float(existing["threshold_amount"])

            # If existing rule allows higher limit without cooling period, conflict occurs!
            if curr_threshold > req_threshold or (req_cooling > 0 and existing["cooling_period_hours"] == 0):
                return PolicyMappingItem(
                    mapping_id=f"MAP-{index:03d}",
                    obligation_id=obl.id,
                    clause_id=obl.clause_id,
                    internal_policy_id=existing["policy_ref"],
                    existing_rule_ref="upi_daily_limit",
                    conflict_type=ConflictType.CONFLICT,
                    description=(
                        f"Existing rule 'upi_daily_limit' permits instant clearing up to ₹{curr_threshold:,.0f} "
                        f"without cooling. Mandate requires threshold of ₹{req_threshold:,.0f} and "
                        f"{req_cooling}-hour cooling period."
                    ),
                    suggested_resolution=(
                        f"Lower threshold from ₹{curr_threshold:,.0f} to ₹{req_threshold:,.0f} "
                        f"and add mandatory {req_cooling}h cooling period condition."
                    ),
                    status=ConflictStatus.DETECTED,
                    details={
                        "existing_rule": existing,
                        "obligation_condition": obl.condition_json,
                    },
                )

        # Check for existing rule for RTGS or wire
        if req_channel == "RTGS":
            # No existing RTGS threshold rule in baseline -> GAP!
            return PolicyMappingItem(
                mapping_id=f"MAP-{index:03d}",
                obligation_id=obl.id,
                clause_id=obl.clause_id,
                internal_policy_id=None,
                existing_rule_ref=None,
                conflict_type=ConflictType.GAP,
                description=f"No active system rule or policy enforces RTGS threshold for ₹{req_threshold:,.0f}.",
                suggested_resolution="Synthesize new Rule DSL specification to enforce RTGS wire threshold.",
                status=ConflictStatus.DETECTED,
                details={"obligation_condition": obl.condition_json},
            )

        # Default: New rule gap
        return PolicyMappingItem(
            mapping_id=f"MAP-{index:03d}",
            obligation_id=obl.id,
            clause_id=obl.clause_id,
            internal_policy_id=None,
            existing_rule_ref=None,
            conflict_type=ConflictType.GAP,
            description=f"No existing rule mapped for channel {req_channel}.",
            suggested_resolution="Author new Rule DSL for obligation.",
            status=ConflictStatus.DETECTED,
            details={"obligation_condition": obl.condition_json},
        )

    def resolve_mapping_conflict(
        self, mapping: PolicyMappingItem, resolution_choice: str = "SUPERSEDE"
    ) -> PolicyMappingItem:
        """
        Marks conflict resolved when the Rule Author Agent incorporates the resolution.
        """
        mapping.status = ConflictStatus.RESOLVED
        mapping.details["resolution_choice"] = resolution_choice
        return mapping
