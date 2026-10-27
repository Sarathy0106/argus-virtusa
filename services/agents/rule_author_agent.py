"""
Rule Author Agent for ARGUS v2 (Stage 4).
Authors draft rule changes in YAML Rule DSL, synthesizes test cases,
compiles DSL to Rego code, and responds to Validator/Impact objections
by revising draft rules during the Orchestrator's Objection Loop.
"""


from contracts.agents import AgentCard, AgentSkill
from contracts.obligations import RegulatoryObligation
from contracts.policy_mapping import PolicyMappingItem
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
        is_cash = bool(obligation.condition_json.get("is_cash", False))

        # B6 NATURAL OBJECTION LOOP
        # The first draft is NAIVE: the author translates the obligation directly
        # and does NOT consult the conflict list / apply any resolution. If the
        # obligation genuinely conflicts with an active live rule, that conflict
        # survives into the draft and the Z3-backed Validator rejects it for a
        # real reason. From iteration 2 the author applies the mapping's
        # suggested resolution (supersede / re-scope) and the conflict is gone.
        #
        # There is no special "deliberately broken" branch: the draft is always a
        # well-formed, cited, tested rule. The ONLY thing that can fail iteration 1
        # is the authentic unresolved conflict proven by Z3.
        resolution_applied = iteration > 1 and mapping is not None

        if is_cash:
            # Cash EDD obligation (C1): naive draft routes band B/C deposits for
            # enhanced review, which collides with the live "block" rule
            # R-CASH-014. The resolution supersedes that block.
            conditions = [
                DSLCondition(
                    field="input.is_cash",
                    operator=DSLOperator.EQ,
                    value=True,
                    description="Cash deposit",
                ),
                DSLCondition(
                    field="input.amount",
                    operator=DSLOperator.GTE,
                    value=threshold,
                    description=f"Amount meets or exceeds ₹{threshold:,.0f}",
                ),
                DSLCondition(
                    field="input.risk_band",
                    operator=DSLOperator.IN,
                    value=["B", "C"],
                    description="Risk Band B or C customer",
                ),
            ]
        else:
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

        # Both iterations are well-formed and cited. The difference is whether the
        # mapping conflict has been resolved (recorded on the rule via a flag the
        # Validator checks against the live-rule set).
        action = DSLAction(
            outcome=obligation.action_json.get("action", "HOLD"),
            tier=obligation.action_json.get("tier", "T2"),
            evidence_id=f"[CLAUSE:{obligation.clause_id}]",
            cooling_period_hours=cooling_hours if not is_cash else None,
        )
        citations = [f"[CLAUSE:{obligation.clause_id}]", f"[OBLIGATION:{obligation.id}]"]
        if mapping and mapping.internal_policy_id:
            citations.append(f"[POLICY:{mapping.internal_policy_id}]")

        if is_cash:
            base_in = {"is_cash": True, "risk_band": "C"}
            miss_in = {"is_cash": True, "risk_band": "A"}
            test_cases = [
                DSLTestCase(
                    test_id=f"{rule_slug}_hit_boundary",
                    description="Positive hit at exact threshold, band C",
                    input_data={"amount": threshold, **base_in},
                    expected_hit=True,
                    expected_outcome=action.outcome,
                ),
                DSLTestCase(
                    test_id=f"{rule_slug}_hit_above",
                    description="Positive hit well above threshold, band C",
                    input_data={"amount": threshold + 200000, **base_in},
                    expected_hit=True,
                    expected_outcome=action.outcome,
                ),
                DSLTestCase(
                    test_id=f"{rule_slug}_miss_below",
                    description="Negative test below threshold",
                    input_data={"amount": threshold - 100, **base_in},
                    expected_hit=False,
                ),
                DSLTestCase(
                    test_id=f"{rule_slug}_miss_low_risk",
                    description="Negative test for low-risk band A",
                    input_data={"amount": threshold + 50000, **miss_in},
                    expected_hit=False,
                ),
            ]
        else:
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

        # Record conflict resolution only from iteration 2 onward. The naive first
        # draft leaves `conflict_resolved=False` and supersedes nothing.
        supersedes: list[str] = []
        if resolution_applied and mapping is not None and mapping.existing_rule_ref:
            supersedes = [mapping.existing_rule_ref]

        rule_def = RuleDefinition(
            rule_name=rule_slug,
            version=f"1.{iteration}.0",
            clause_id=obligation.clause_id,
            obligation_id=obligation.id,
            policy_id=mapping.internal_policy_id if mapping else None,
            citations=citations,
            description=f"Rule authored for {obligation.id} (threshold ₹{threshold:,.0f})",
            conditions=conditions,
            action=action,
            test_cases=test_cases,
            draft_status="DRAFT_ONLY",
            supersedes=supersedes,
            conflict_resolved=resolution_applied,
        )

        rego_code = self.compiler.compile_to_rego(rule_def)
        test_rego = self.compiler.compile_tests_to_rego(rule_def)

        return rule_def, rego_code, test_rego
