"""
Rule Author Agent for ARGUS v2 (Stage 4).
Authors draft rule changes in YAML Rule DSL, synthesizes test cases,
compiles DSL to Rego code, and responds to Validator/Impact objections
by revising draft rules during the Orchestrator's Objection Loop.
"""

from typing import Any

from contracts.agents import AgentCard, AgentSkill
from contracts.obligations import RegulatoryObligation
from contracts.policy_mapping import ConflictStatus, PolicyMappingItem
from contracts.rule_dsl import (
    DSLAction,
    DSLCondition,
    DSLOperator,
    DSLTestCase,
    RuleDefinition,
)
from contracts.validation import ValidationObjection
from services.agents.crypto import AgentKeyPair
from services.regcompiler.dsl_compiler import RuleDSLCompiler


class RuleAuthorAgent:
    def __init__(self, key_pair: AgentKeyPair | None = None, compiler: RuleDSLCompiler | None = None):
        self.key_pair = key_pair or AgentKeyPair()
        self.compiler = compiler or RuleDSLCompiler()
        self.agent_id = "agent.rule_author"
        self.card = AgentCard(
            agent_id=self.agent_id,
            name="Rule Author Agent",
            version="2.0.0",
            public_key=self.key_pair.public_key_hex,
            skills=[
                AgentSkill(
                    name="rule.author_dsl",
                    description="Authors Rule DSL, synthesizes test cases, and compiles Rego policies.",
                )
            ],
        )

    def author_rule(
        self,
        obligation: RegulatoryObligation,
        mapping: PolicyMappingItem | None = None,
        objection: ValidationObjection | None = None,
        iteration: int = 1,
    ) -> tuple[RuleDefinition, str, str]:
        """
        Authors a RuleDefinition in Rule DSL, compiles to Rego, and returns (rule_def, rego_code, test_rego).
        If objection is provided or iteration > 1, applies corrective fixes.
        """
        rule_slug = obligation.rule_ref.lower().replace("-", "_")
        target_channel = obligation.condition_json.get("channel", "UPI")
        threshold = float(obligation.condition_json.get("threshold_amount", 50000.0))
        cooling_hours = int(obligation.condition_json.get("cooling_period_hours", 4))

        # Intentionally demonstrate Objection Loop if iteration == 1 and mapping has detected conflict
        if iteration == 1 and mapping and mapping.status == ConflictStatus.DETECTED:
            # Flawed draft: leaves conflict unaddressed or lacks citation
            conditions = [
                DSLCondition(
                    field="input.amount",
                    operator=DSLOperator.GTE,
                    value=threshold,
                    description=f"Transaction amount meets or exceeds threshold {threshold}",
                ),
                DSLCondition(
                    field="input.channel",
                    operator=DSLOperator.EQ,
                    value=target_channel,
                    description=f"Transaction channel is {target_channel}",
                ),
            ]
            action = DSLAction(
                outcome="HOLD",
                tier="T1",
                evidence_id="UNCITED_DRAFT",  # Intentionally missing proper clause citation
                cooling_period_hours=None,  # Missing required cooling period
            )
            # Lacking sufficient test cases
            test_cases = [
                DSLTestCase(
                    test_id=f"{rule_slug}_t1",
                    description="Hit test above threshold",
                    input_data={"amount": threshold + 1000, "channel": target_channel},
                    expected_hit=True,
                )
            ]
            citations = []  # Empty citations to test validation gate

        else:
            # Corrected Draft: Incorporates full cooling period, valid citations, boundary unit tests
            conditions = [
                DSLCondition(
                    field="input.amount",
                    operator=DSLOperator.GTE,
                    value=threshold,
                    description=f"Transaction amount meets or exceeds ₹{threshold:,.0f}",
                ),
                DSLCondition(
                    field="input.channel",
                    operator=DSLOperator.EQ,
                    value=target_channel,
                    description=f"Channel must match {target_channel}",
                ),
            ]
            action = DSLAction(
                outcome=obligation.action_json.get("action", "HOLD"),
                tier=obligation.action_json.get("tier", "T2"),
                evidence_id=f"[CLAUSE:{obligation.clause_id}]",
                cooling_period_hours=cooling_hours,
            )
            citations = [f"[CLAUSE:{obligation.clause_id}]", f"[OBLIGATION:{obligation.id}]"]
            if mapping and mapping.internal_policy_id:
                citations.append(f"[POLICY:{mapping.internal_policy_id}]")

            test_cases = [
                DSLTestCase(
                    test_id=f"{rule_slug}_hit_boundary",
                    description="Positive hit at exact threshold",
                    input_data={"amount": threshold, "channel": target_channel},
                    expected_hit=True,
                    expected_outcome=action.outcome,
                ),
                DSLTestCase(
                    test_id=f"{rule_slug}_hit_above",
                    description="Positive hit well above threshold",
                    input_data={"amount": threshold + 25000, "channel": target_channel},
                    expected_hit=True,
                    expected_outcome=action.outcome,
                ),
                DSLTestCase(
                    test_id=f"{rule_slug}_miss_below",
                    description="Negative test below threshold",
                    input_data={"amount": threshold - 100, "channel": target_channel},
                    expected_hit=False,
                ),
                DSLTestCase(
                    test_id=f"{rule_slug}_miss_other_channel",
                    description="Negative test for different channel",
                    input_data={"amount": threshold + 5000, "channel": "NEFT"},
                    expected_hit=False,
                ),
            ]

        rule_def = RuleDefinition(
            rule_name=rule_slug,
            version=f"1.{iteration}.0",
            clause_id=obligation.clause_id,
            obligation_id=obligation.id,
            policy_id=mapping.internal_policy_id if mapping else None,
            citations=citations,
            description=f"Rule authored for {obligation.id} on channel {target_channel} with threshold ₹{threshold:,.0f}",
            conditions=conditions,
            action=action,
            test_cases=test_cases,
            draft_status="DRAFT_ONLY",
        )

        rego_code = self.compiler.compile_to_rego(rule_def)
        test_rego = self.compiler.compile_tests_to_rego(rule_def)

        return rule_def, rego_code, test_rego
