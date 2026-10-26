"""
Comprehensive Unit Tests for ARGUS v2 — Regulatory Circular to Live Rule Engine.
Tests all 10 stages:
1. Circular Intake & Airlock
2. Obligation Extraction & Applicability
3. Policy Mapping & Conflict Detection
4. Rule Authoring in Rule DSL
5. Backtesting in Sandbox
6. Impact Analysis
7. Validation Gate & Objection Loop
8. Maker-Checker Dual Approval
9. Shadow Deployment
10. Canary Ramp & Sub-Minute Automatic Rollback
"""

import pytest

from contracts.bank_profile import BankProfile, BankType, ProductType
from contracts.deployment import DeploymentStage
from contracts.obligations import ApplicabilityStatus
from contracts.policy_mapping import ConflictStatus, ConflictType
from contracts.rule_dsl import DSLOperator
from contracts.validation import ObjectionCode
from services.agents.broker import CapabilityBroker
from services.agents.deployment_agent import UnauthorizedDeploymentError
from services.ingest.simulator import SyntheticTransactionGenerator
from services.ledger.ledger import AuditLedger
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator


SAMPLE_CIRCULAR_TEXT = """
Reserve Bank of India
Notification: RBI/2024-25/118
Master Direction – Enhanced Risk Management Framework for Immediate and UPI Transactions

Section 1: Scope and Applicability
These directions apply to all Scheduled Commercial Banks and Payment System Operators operating UPI channels.

Section 2: High-Value Immediate Transfer Cooling Period
All regulated entities shall enforce a mandatory cooling period of 4 hours for any retail immediate payment
or UPI transaction where the single transaction amount meets or exceeds INR 50,000. During the cooling period,
the funds shall be held in escrow pending step-up multi-factor authentication or analytical clearance.
Effective deadline: w.e.f 2024-11-01.

Section 3: High-Value Cross-Border RTGS Outflows
All Scheduled Commercial Banks facilitating outbound cross-border RTGS payments exceeding INR 500,000
must perform real-time sanction checks and secondary compliance officer clearance.
Effective deadline: w.e.f 2024-12-31.
"""


@pytest.fixture
def test_bank_profile() -> BankProfile:
    return BankProfile(
        bank_id="APEX_IN_001",
        bank_name="Apex Bank of India",
        bank_type=BankType.SCHEDULED_COMMERCIAL_BANK,
        licenses=["RETAIL_BANKING", "COMMERCIAL_BANKING", "PAYMENT_SYSTEM_OPERATOR"],
        active_products=[ProductType.UPI, ProductType.IMPS, ProductType.RTGS],
        supported_channels=["UPI", "MOBILE", "NET_BANKING"],
    )


@pytest.fixture
def non_upi_bank_profile() -> BankProfile:
    # A regional rural or cooperative bank without UPI license
    return BankProfile(
        bank_id="RURAL_COOP_099",
        bank_name="Gramin Cooperative Bank",
        bank_type=BankType.COOPERATIVE_BANK,
        licenses=["RETAIL_BANKING"],
        active_products=[ProductType.RETAIL_DEPOSITS],
        supported_channels=["BRANCH"],
    )


@pytest.fixture
def historical_txns():
    gen = SyntheticTransactionGenerator(seed=101)
    return gen.generate_dataset(150)


def test_stage_1_circular_intake(test_bank_profile):
    orchestrator = RegulatoryRuleOrchestrator()
    res = orchestrator.intake_agent.process_circular(
        circular_id="RBI-2024-118",
        circular_title="Enhanced Risk Management for UPI",
        raw_text=SAMPLE_CIRCULAR_TEXT,
    )
    assert res["circular_id"] == "RBI-2024-118"
    assert res["clause_count"] >= 3
    assert len(res["document_hash"]) == 64
    assert res["airlocked"] is True


def test_stage_2_applicability_engine(test_bank_profile, non_upi_bank_profile):
    orchestrator = RegulatoryRuleOrchestrator()
    clauses = orchestrator.intake_agent.process_circular(
        circular_id="RBI-2024-118",
        circular_title="Enhanced Risk Management for UPI",
        raw_text=SAMPLE_CIRCULAR_TEXT,
    )["clauses"]

    # 1. Evaluate against Apex Bank (Fully applicable)
    apex_obligations = orchestrator.obligation_agent.extract_obligations(clauses, test_bank_profile)
    applicable = [o for o in apex_obligations if o.applicability_status == ApplicabilityStatus.APPLICABLE]
    assert len(applicable) >= 1
    assert applicable[0].condition_json["threshold_amount"] == 50000.0
    assert applicable[0].condition_json["channel"] == "UPI"

    # 2. Evaluate against Rural Coop Bank (Not applicable)
    rural_obligations = orchestrator.obligation_agent.extract_obligations(clauses, non_upi_bank_profile)
    for obl in rural_obligations:
        assert obl.applicability_status == ApplicabilityStatus.NOT_APPLICABLE
        assert "does not offer required products" in obl.applicability_rationale or "Obligation applies strictly" in obl.applicability_rationale


def test_stage_3_policy_mapping_conflict_and_gap(test_bank_profile):
    orchestrator = RegulatoryRuleOrchestrator()
    clauses = orchestrator.intake_agent.process_circular(
        circular_id="RBI-2024-118",
        circular_title="Enhanced Risk Management for UPI",
        raw_text=SAMPLE_CIRCULAR_TEXT,
    )["clauses"]
    obligations = orchestrator.obligation_agent.extract_obligations(clauses, test_bank_profile)
    mapping_res = orchestrator.policy_mapper_agent.map_obligations(obligations, bank_id=test_bank_profile.bank_id)

    # Must find one CONFLICT with upi_daily_limit (existing allows 100k without cooling, circular mandates 50k + 4h cooling)
    conflicts = [m for m in mapping_res.mappings if m.conflict_type == ConflictType.CONFLICT]
    assert len(conflicts) >= 1
    assert conflicts[0].existing_rule_ref == "upi_daily_limit"
    assert "upi_daily_limit" in conflicts[0].description

    # Must find GAP for RTGS
    gaps = [m for m in mapping_res.mappings if m.conflict_type == ConflictType.GAP]
    assert len(gaps) >= 1


def test_stage_4_rule_authoring_and_rego_compiler(test_bank_profile):
    orchestrator = RegulatoryRuleOrchestrator()
    clauses = orchestrator.intake_agent.process_circular(
        circular_id="RBI-2024-118",
        circular_title="Enhanced Risk Management for UPI",
        raw_text=SAMPLE_CIRCULAR_TEXT,
    )["clauses"]
    obligations = orchestrator.obligation_agent.extract_obligations(clauses, test_bank_profile)
    mapping_res = orchestrator.policy_mapper_agent.map_obligations(obligations, bank_id=test_bank_profile.bank_id)

    # Corrected authoring on iteration 2
    rule_def, rego, tests = orchestrator.rule_author_agent.author_rule(
        obligation=obligations[0],
        mapping=mapping_res.mappings[0],
        iteration=2,
    )
    assert rule_def.rule_name == "upi_cooling_period_50000"
    assert rule_def.action.cooling_period_hours == 4
    assert len(rule_def.citations) >= 2
    assert "package argus.compiled.upi_cooling_period_50000" in rego
    assert "input.amount >= 50000.0" in rego
    assert "test_upi_cooling_period_50000" in tests


def test_stage_5_backtest_and_stage_6_impact(test_bank_profile, historical_txns):
    orchestrator = RegulatoryRuleOrchestrator()
    clauses = orchestrator.intake_agent.process_circular(
        circular_id="RBI-2024-118",
        circular_title="Enhanced Risk Management for UPI",
        raw_text=SAMPLE_CIRCULAR_TEXT,
    )["clauses"]
    obligations = orchestrator.obligation_agent.extract_obligations(clauses, test_bank_profile)
    rule_def, _, _ = orchestrator.rule_author_agent.author_rule(
        obligation=obligations[0],
        iteration=2,
    )

    # Backtest
    backtest = orchestrator.backtest_agent.run_backtest(rule_def, historical_txns)
    assert backtest.total_txns == len(historical_txns)
    assert backtest.candidate_alerts >= 0

    # Impact
    impact = orchestrator.impact_agent.analyze_impact(backtest)
    assert len(impact.segments) == 3
    assert impact.estimated_ops_hours_per_day >= 0.0


def test_objection_loop_end_to_end(test_bank_profile, historical_txns):
    """
    Demonstrates demo script step 4:
    Iteration 1 draft has unaddressed conflict & lacks citations -> Validator rejects!
    Orchestrator captures objection and re-routes back to Stage 3/4.
    Iteration 2 resolves conflict and adds citations -> Validator passes!
    """
    orchestrator = RegulatoryRuleOrchestrator()
    state = orchestrator.run_pipeline_to_approval(
        circular_id="RBI-2024-118",
        circular_title="Enhanced Risk Management for UPI",
        circular_text=SAMPLE_CIRCULAR_TEXT,
        bank_profile=test_bank_profile,
        historical_txns=historical_txns,
        simulate_objection_loop=True,
    )

    # Must have encountered at least 1 objection and re-routed
    assert len(state.objection_history) >= 1
    assert state.objection_history[0].code in (
        ObjectionCode.UNRESOLVED_CONFLICT,
        ObjectionCode.UNCITED_CLAUSE,
    )
    # Must have completed iteration 2 successfully
    assert state.iteration_count == 2
    assert state.validation_report.passed is True
    assert state.validation_report.certificate_id is not None
    assert state.stage_name == "HUMAN_APPROVAL_PENDING"


def test_stage_8_maker_checker_approval_gate(test_bank_profile, historical_txns):
    orchestrator = RegulatoryRuleOrchestrator()
    state = orchestrator.run_pipeline_to_approval(
        circular_id="RBI-2024-118",
        circular_title="Enhanced Risk Management for UPI",
        circular_text=SAMPLE_CIRCULAR_TEXT,
        bank_profile=test_bank_profile,
        historical_txns=historical_txns,
    )

    # Attempt to deploy without approval must be blocked
    with pytest.raises(UnauthorizedDeploymentError):
        orchestrator.deployment_agent.deploy_to_shadow(state.rule_definition, "INVALID_TOKEN")

    # Maker cannot be the Checker (Self-approval blocked)
    with pytest.raises(PermissionError):
        orchestrator.grant_dual_approval(state, maker_id="alice", checker_id="alice")

    # Dual independent approval succeeds
    token = orchestrator.grant_dual_approval(
        state, maker_id="compliance_analyst_alice", checker_id="compliance_officer_bob"
    )
    assert token.is_valid is True
    assert state.approval_status == "APPROVED"


def test_stage_9_shadow_and_stage_10_canary_rollback(test_bank_profile, historical_txns):
    """
    Demonstrates demo script steps 6 & 7:
    Maker-checker approves -> shadow mode runs -> canary ramps -> forced threshold breach triggers automatic rollback!
    """
    orchestrator = RegulatoryRuleOrchestrator()
    state = orchestrator.run_pipeline_to_approval(
        circular_id="RBI-2024-118",
        circular_title="Enhanced Risk Management for UPI",
        circular_text=SAMPLE_CIRCULAR_TEXT,
        bank_profile=test_bank_profile,
        historical_txns=historical_txns,
    )
    orchestrator.grant_dual_approval(
        state, maker_id="analyst_alice", checker_id="officer_bob"
    )

    # Run shadow mode and canary ramp with simulated breach at 50%
    state = orchestrator.execute_shadow_and_rollout(
        state=state,
        live_transactions=historical_txns,
        force_canary_breach=True,
    )

    # Shadow mode evaluated
    assert state.shadow_evaluation is not None
    assert state.shadow_evaluation.concordance_percentage > 0.0

    # Automatic Rollback triggered
    assert state.deployment_stage == DeploymentStage.ROLLED_BACK
    assert state.rollback_record is not None
    assert state.rollback_record.recovery_time_ms < 1000.0  # Under 1 second target!
    assert state.rollback_record.to_version == "1.0.0"
    assert "FORCED_SAFETY_DRIFT_BREACH" in state.rollback_record.reason

    # Verify audit ledger contains complete hash chain
    assert len(state.audit_hashes) >= 5
    assert orchestrator.audit_ledger.verify_chain() is True
