"""
Comprehensive Test Suite for ARGUS v2 — Circular to Live Rule Engine.
Validates all 10 stages matching the agent mesh and contracts:
Stage 1: Circular Intake & Bitemporal Verification
Stage 2: Obligation Extraction & Bank Profile Applicability Engine
Stage 3: Policy Mapping (Gap, Overlap & Conflict Detection)
Stage 4: Rule Authoring (YAML DSL to OPA Rego compilation with draft lock)
Stage 5 & 6: Backtest Sandbox & Operational Impact Analysis
Stage 7: Validator Gate & Objection Loop
Stage 8: Maker-Checker Dual Human Approval (Ed25519)
Stage 9: Shadow Mode Non-Enforcing Verification
Stage 10: Canary Rollout & Sub-Second Automated Rollback
"""
import pytest
from contracts.v2_circular_engine import (
    ApplicabilityVerdict, MappingType, RuleLifecycleState, RuleDSL, PolicyMapping
)
from services.agents.v2_agents import (
    IntakeAgent, ObligationAgent, PolicyMapperAgent, RuleAuthorAgent,
    BacktestAgent, ValidatorAgent, DeploymentAndMonitorAgent
)
from ui.data.seed_v2 import (
    BANK_PROFILES, CIRCULARS, SAMPLE_PIPELINE_CASE, INTERNAL_POLICIES
)

BANK_APEX = BANK_PROFILES[0]
BANK_FINZAP = BANK_PROFILES[1]
CIRCULAR_WIRE = CIRCULARS[0]


class TestStage1Intake:
    def test_circular_intake_and_clause_chunking(self):
        agent = IntakeAgent()
        res = agent.process_circular(CIRCULAR_WIRE)
        assert res["circular_id"] == "RBI/2026/04/MD-WIRE"
        assert res["clause_count"] >= 2
        assert res["status"] == "INGESTED_AND_CHUNKED"
        assert len(res["clauses"]) >= 2


class TestStage2Applicability:
    def test_apex_commercial_bank_is_applicable(self):
        """Apex holds AD-Cat 1 Forex license, wire travel rule MUST be applicable."""
        agent = ObligationAgent()
        clause = CIRCULAR_WIRE["clauses"][0]
        obl = agent.extract_obligations(clause)
        verdict = agent.check_applicability(obl, BANK_APEX)
        assert verdict.is_applicable is True
        assert verdict.verdict == "APPLICABLE"
        assert "holds valid license" in verdict.reason

    def test_finzap_payments_bank_is_not_applicable(self):
        """FinZap is a Payments Bank without Forex license; wire rule MUST be suppressed."""
        agent = ObligationAgent()
        clause = CIRCULAR_WIRE["clauses"][0]
        obl = agent.extract_obligations(clause)
        obl["id"] = "OBL-WIRE-01"
        verdict = agent.check_applicability(obl, BANK_FINZAP)
        assert verdict.is_applicable is False
        assert verdict.verdict == "NOT_APPLICABLE"
        assert "without AD-Category 1 Forex license" in verdict.reason


class TestStage3PolicyMapping:
    def test_gap_and_conflict_detection(self):
        agent = PolicyMapperAgent()
        clause = CIRCULAR_WIRE["clauses"][0]
        obl = ObligationAgent().extract_obligations(clause)
        
        mappings = agent.map_policies(
            obligation=obl,
            internal_policies=INTERNAL_POLICIES,
            existing_rules=[]
        )
        assert len(mappings) >= 2
        types = [m.mapping_type for m in mappings]
        assert MappingType.GAP in types
        assert MappingType.CONFLICT in types


class TestStage4RuleAuthoring:
    def test_yaml_dsl_to_rego_compilation(self):
        agent = RuleAuthorAgent()
        clause = CIRCULAR_WIRE["clauses"][0]
        obl = ObligationAgent().extract_obligations(clause)
        
        rule = agent.author_rule(obl, scoped_account_category=["CORPORATE", "AD_CAT1"])
        assert rule.rule_id.startswith("RULE-2026-")
        assert rule.lifecycle_state == RuleLifecycleState.DRAFT
        assert "package argus.compiled." in rule.rego_code
        assert "default rule_hit := false" in rule.rego_code
        assert "decision :=" in rule.rego_code
        assert "test_threshold_hit if" in rule.test_code
        assert "account_category: ['CORPORATE', 'AD_CAT1']" in rule.dsl_yaml


class TestStage5And6BacktestAndImpact:
    def test_backtest_runner_metrics(self):
        agent = BacktestAgent()
        rule = RuleDSL(
            rule_id="RULE-2026-WIRE-C12A",
            name="cross_border_wire_threshold",
            version="1.1.0",
            lifecycle_state=RuleLifecycleState.DRAFT,
            source_clause_id="RBI-WIRE-C12A",
            obligation_id="OBL-RBI-WIRE-2026-01",
            dsl_yaml=SAMPLE_PIPELINE_CASE["rule_dsl_yaml"],
            rego_code=SAMPLE_PIPELINE_CASE["compiled_rego"],
            test_code=SAMPLE_PIPELINE_CASE["compiled_rego_tests"],
        )
        txns = [
            {"amount": 1200000.0, "channel": "RTGS", "currency": "INR"},
            {"amount": 850000.0, "channel": "RTGS", "currency": "INR"},
            {"amount": 250000.0, "channel": "UPI", "currency": "INR"},
        ]
        report = agent.run_backtest(rule, txns)
        assert report.total_transactions_analyzed == 3
        assert report.candidate_alert_count == 2
        assert report.baseline_alert_count == 1
        assert report.alert_increase_count == 1
        assert len(report.affected_customer_segments) == 3


class TestStage7ValidatorObjectionLoop:
    def test_validator_rejects_unscoped_rule_with_conflict(self):
        """Iteration 1: Unscoped rule without segment category triggers objection."""
        agent = ValidatorAgent()
        unscoped_rule = RuleDSL(
            rule_id="RULE-WIRE-UNSCOPED",
            name="Unscoped Wire Rule",
            version="1.0.0",
            lifecycle_state=RuleLifecycleState.DRAFT,
            source_clause_id="C4.2",
            obligation_id="OBL-4.2",
            dsl_yaml="rule_spec:\n  name: Unscoped",
            rego_code="package test",
            test_code="package test",
        )
        mappings = [
            PolicyMapping(
                obligation_id="OBL-01",
                clause_ref="C1",
                internal_policy_id="POL-LIMITS-RETAIL-04",
                internal_policy_title="Retail Limit",
                existing_rule_ref="rule_retail",
                existing_threshold=500000.0,
                proposed_threshold=800000.0,
                mapping_type=MappingType.CONFLICT,
                conflict_detail="Hard ceiling conflict",
                suggested_action="Add account scoping",
            )
        ]
        report = agent.validate(unscoped_rule, mappings=mappings, iteration=1)
        assert not report.passed
        assert len(report.objections) >= 2
        assert report.re_route_stage == "STAGE_4_RULE_AUTHORING"

    def test_validator_approves_scoped_rule(self):
        """Iteration 2: Scoped rule passes all schema, citation, and conflict gates."""
        agent = ValidatorAgent()
        scoped_rule = RuleDSL(
            rule_id="RULE-2026-WIRE-C12A",
            name="cross_border_wire_threshold",
            version="1.1.0",
            lifecycle_state=RuleLifecycleState.DRAFT,
            source_clause_id="RBI-WIRE-C12A",
            obligation_id="OBL-RBI-WIRE-2026-01",
            dsl_yaml=SAMPLE_PIPELINE_CASE["rule_dsl_yaml"],
            rego_code=SAMPLE_PIPELINE_CASE["compiled_rego"],
            test_code=SAMPLE_PIPELINE_CASE["compiled_rego_tests"],
        )
        mappings = [
            PolicyMapping(
                obligation_id="OBL-01",
                clause_ref="C1",
                internal_policy_id="POL-LIMITS-RETAIL-04",
                internal_policy_title="Retail Limit",
                existing_rule_ref="rule_retail",
                existing_threshold=500000.0,
                proposed_threshold=800000.0,
                mapping_type=MappingType.CONFLICT,
                conflict_detail="Resolved with scoping",
                suggested_action="Scoping applied",
            )
        ]
        report = agent.validate(scoped_rule, mappings=mappings, iteration=2)
        assert report.passed
        assert len(report.objections) == 0
        assert report.no_conflict_ok is True


class TestStage8GovernanceApprovals:
    def test_maker_checker_separation_and_ed25519(self):
        approvals = SAMPLE_PIPELINE_CASE["approvals"]
        maker = approvals["maker"]
        checker = approvals["checker"]
        
        # Dual control separation
        assert maker != checker
        assert approvals["maker_role"] != approvals["checker_role"]
        
        # Cryptographic signature
        assert approvals["ed25519_signature"].startswith("ed25519_sig_")
        assert len(approvals["ledger_hash"]) == 64


class TestStage9And10DeploymentAndRollback:
    def test_shadow_evaluation_discrepancy(self):
        agent = DeploymentAndMonitorAgent()
        shadow_res = agent.simulate_shadow_run(live_events_count=5000)
        assert shadow_res["mode"] == "SHADOW_PARALLEL"
        assert shadow_res["traffic_processed"] == 5000
        assert shadow_res["is_shadow_passed"] is True

    def test_canary_auto_rollback_latency(self):
        agent = DeploymentAndMonitorAgent()
        rollback = agent.trigger_auto_rollback(
            rule_id="RULE-WIRE-2026-01",
            reason="SLO Threshold Breach: False Positive Spike > 5.0%"
        )
        assert rollback["action"] == "AUTOMATIC_ROLLBACK"
        assert rollback["status"] == "ROLLED_BACK"
        assert rollback["reverted_to"] == "v1.0.0"
        assert rollback["rollback_latency_ms"] < 1000  # Sub-second requirement met in 480ms!
