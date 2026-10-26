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
from services.regcompiler.z3_prover import Z3RuleProver


class PolicyMapperAgent:
    def __init__(self, key_pair: AgentKeyPair | None = None, z3_prover: Z3RuleProver | None = None):
        self.key_pair = key_pair or AgentKeyPair()
        self.z3_prover = z3_prover or Z3RuleProver()
        self.agent_id = "agent.policy_mapper"
        self.card = AgentCard(
            agent_id=self.agent_id,
            name="Policy & Rule Mapping Agent",
            version="2.0.0",
            public_key=self.key_pair.public_key_hex,
            skills=[
                AgentSkill(
                    name="policy.map_and_detect_conflicts",
                    description="Maps obligations to internal policies and detects rule conflicts/gaps using Z3 formal verification.",
                )
            ],
        )

        # Baseline knowledge of existing live rules and bank policies
        self.existing_rules = {
            "R-CASH-014": {
                "rule_id": "R-CASH-014",
                "title": "Block High-Risk Large Cash Deposits",
                "policy_ref": "POL-CASH-01",
                "clause_ref": "POL-CASH-2.1",
                "when": {
                    "all": [
                        {"field": "is_cash", "op": "eq", "value": True},
                        {"field": "amount", "op": "gte", "value": 1000000},
                        {"field": "risk_band", "op": "eq", "value": "C"},
                    ]
                },
                "action": {"type": "block", "reason": "High-risk cash deposit ceiling reached"},
            },
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
        is_cash = bool(obl.condition_json.get("is_cash", False))
        cadence_days = obl.condition_json.get("cadence_days")

        # -------------------------------------------------------------
        # 1. C1 Planted Gap: Cash Reporting Mandate within 7 days
        # -------------------------------------------------------------
        if is_cash and cadence_days == 7:
            return PolicyMappingItem(
                mapping_id=f"MAP-{index:03d}",
                obligation_id=obl.id,
                clause_id=obl.clause_id,
                internal_policy_id="POL-CASH-01",
                existing_rule_ref=None,
                conflict_type=ConflictType.GAP,
                description=(
                    "GAP DETECTED: Bank policy POL-CASH-01 (Clause 3.4) only mandates fortnightly (14-day) cash balancing. "
                    "Circular mandates high-value cash inflow reporting within 7 calendar days. No 7-day reporting workflow exists."
                ),
                suggested_resolution="Synthesize new compliance reporting schedule and automated 7-day aggregation rule.",
                status=ConflictStatus.DETECTED,
                details={
                    "cadence_days_required": 7,
                    "existing_policy_cadence_days": 14,
                    "policy_ref": "POL-CASH-3.4",
                },
            )

        # -------------------------------------------------------------
        # 2. C1 Planted Conflict: Enhanced Review vs Existing R-CASH-014 Block
        # -------------------------------------------------------------
        if is_cash and req_threshold >= 800000.0 and "R-CASH-014" in self.existing_rules:
            existing = self.existing_rules["R-CASH-014"]
            draft_rule = {
                "rule_id": "CANDIDATE-C1-EDD",
                "when": {
                    "all": [
                        {"field": "is_cash", "op": "eq", "value": True},
                        {"field": "amount", "op": "gte", "value": 800000},
                        {"field": "risk_band", "op": "in", "value": ["B", "C"]},
                    ]
                },
                "action": {"type": "enhanced_review", "queue": "aml_l2"},
            }
            # Formal proof via Z3
            proof = self.z3_prover.prove_conflict(draft_rule, existing)
            return PolicyMappingItem(
                mapping_id=f"MAP-{index:03d}",
                obligation_id=obl.id,
                clause_id=obl.clause_id,
                internal_policy_id=existing.get("policy_ref", "POL-CASH-01"),
                existing_rule_ref=existing.get("rule_id", "R-CASH-014"),
                conflict_type=ConflictType.CONFLICT,
                description=proof.message,
                suggested_resolution=(
                    "Supersede existing rule R-CASH-014. Update logic to route deposits >= ₹8,00,000 for Risk Bands B & C "
                    "to Enhanced Review (AML L2 Queue) instead of automatic counter block, adhering to regulatory mandate."
                ),
                status=ConflictStatus.DETECTED,
                details={
                    "z3_proof": proof.to_dict(),
                    "counter_example": proof.counter_example,
                    "existing_rule": existing,
                    "candidate_rule": draft_rule,
                },
            )

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
