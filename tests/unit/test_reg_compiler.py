import pytest

from contracts.obligations import RegulatoryObligation
from services.ingest.simulator import SyntheticTransactionGenerator
from services.regcompiler.compiler import CompilationResult, RegToRuleCompiler


def test_compiler_code_synthesis():
    compiler = RegToRuleCompiler()
    obligation = RegulatoryObligation(
        id="OBL-RBI-2024-001",
        clause_id="RBI-WIRE-01",
        actor="Commercial Bank",
        trigger_event="TRANSACTION_SUBMITTED",
        condition_json={"threshold_amount": 800000.0, "channel": "RTGS"},
        action_json={"action": "HOLD", "tier": "T2"},
        rule_ref="cross_border_wire_threshold",
        severity="HIGH",
    )

    rego, test_rego = compiler.compile_obligation_to_rego(obligation)
    assert "package argus.compiled.cross_border_wire_threshold" in rego
    assert "input.amount >= 800000.0" in rego
    assert "test_threshold_hit" in test_rego


def test_compiler_historical_impact_simulation():
    compiler = RegToRuleCompiler()
    gen = SyntheticTransactionGenerator(seed=42)
    history = gen.generate_dataset(100)

    obligation = RegulatoryObligation(
        id="OBL-TEST-002",
        clause_id="CLAUSE-TEST",
        actor="Bank",
        trigger_event="TXN",
        condition_json={"threshold_amount": 40000.0, "channel": "UPI"},
        action_json={"action": "HOLD", "tier": "T1"},
        rule_ref="upi_high_value_monitor",
    )

    report = compiler.simulate_historical_impact(obligation, history)
    assert report.total_txns_analyzed == len(history)
    assert report.new_alert_count >= 0
    assert report.delta_percentage >= 0.0


def test_compiler_maker_checker_publishing_gate(tmp_path):
    compiler = RegToRuleCompiler()
    obligation = RegulatoryObligation(
        id="OBL-TEST-003",
        clause_id="CLAUSE-TEST",
        actor="Bank",
        trigger_event="TXN",
        condition_json={"threshold_amount": 50000.0, "channel": "UPI"},
        action_json={"action": "HOLD", "tier": "T1"},
        rule_ref="upi_threshold_published",
    )
    rego, test_rego = compiler.compile_obligation_to_rego(obligation)
    compilation = CompilationResult(
        obligation=obligation, draft_rego_code=rego, draft_test_code=test_rego
    )

    # Attempting to publish without dual signoff must fail
    with pytest.raises(PermissionError):
        compiler.publish_rule_bundle(
            compilation, maker_id="alice", checker_id="alice", target_policy_dir=tmp_path
        )

    # Dual signoff succeeds
    published = compiler.publish_rule_bundle(
        compilation,
        maker_id="compliance_maker_alice",
        checker_id="compliance_checker_bob",
        target_policy_dir=tmp_path,
    )
    assert published.published is True
    assert published.bundle_version == "1.1.0"
    assert (tmp_path / "upi_threshold_published.rego").exists()
    assert compiler.audit_ledger.count() == 1
