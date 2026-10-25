import pytest

from contracts.decisions import DecisionRecord
from services.ledger.ledger import AuditChainIntegrityError, AuditLedger
from services.ledger.replay import ReplayEngine
from services.policy.engine import PolicyEngine


def test_audit_ledger_chain_and_tamper_detection():
    ledger = AuditLedger()

    # Append 3 events
    ledger.append("INIT", "SYS-01", "admin", {"step": 1})
    e2 = ledger.append("RULE_LOAD", "POL-01", "system", {"bundle": "1.0.0"})
    e3 = ledger.append("DECISION", "DEC-01", "agent.txn_risk", {"verdict": "HOLD"})

    assert ledger.count() == 3
    assert ledger.verify_integrity() is True

    # Tamper with event 2's payload
    e2.payload["bundle"] = "TAMPERED_BUNDLE"
    # Tampering with payload without re-hashing breaks verification
    # Or tampering with prev_hash
    original_prev = e3.prev_hash
    e3.prev_hash = "TAMPERED_PREV_HASH"

    with pytest.raises(AuditChainIntegrityError):
        ledger.verify_integrity()

    # Restore
    e3.prev_hash = original_prev


def test_replay_determinism_exact_hash_match():
    policy_engine = PolicyEngine()
    replay_engine = ReplayEngine(policy_engine)

    input_data = {"amount": 49500.0, "structuring_window_count_24h": 3, "location_country": "IND"}

    eval_result = policy_engine.evaluate_local(input_data)

    archived = DecisionRecord.create(
        decision_id="DEC-ORIGINAL-001",
        transaction_id="TXN-ORIGINAL-001",
        input_data=input_data,
        rule_bundle_ver="1.0.0",
        model_ver="lgb_v0.1",
        risk_score=0.89,
        outcome=eval_result.outcome,
        tier=eval_result.tier,
        evidence_ids=eval_result.evidence_ids,
    )

    # Replay
    report = replay_engine.replay_decision(archived, input_data)

    assert report.replayed_success is True
    assert report.input_hash_match is True
    assert report.output_hash_match is True
    assert report.replayed_outcome == "HOLD"
    assert report.replayed_tier == "T1"
    assert "aml_structuring_window" in report.replayed_evidence_ids
    assert len(report.delta) == 0


def test_replay_drift_detection_on_altered_input():
    policy_engine = PolicyEngine()
    replay_engine = ReplayEngine(policy_engine)

    original_input = {
        "amount": 49500.0,
        "structuring_window_count_24h": 3,
        "location_country": "IND",
    }
    eval_result = policy_engine.evaluate_local(original_input)

    archived = DecisionRecord.create(
        decision_id="DEC-ORIGINAL-002",
        transaction_id="TXN-ORIGINAL-002",
        input_data=original_input,
        rule_bundle_ver="1.0.0",
        model_ver="lgb_v0.1",
        risk_score=0.89,
        outcome=eval_result.outcome,
        tier=eval_result.tier,
        evidence_ids=eval_result.evidence_ids,
    )

    # Replay with altered input (amount changed)
    altered_input = dict(original_input)
    altered_input["amount"] = 5000.0  # clean amount

    report = replay_engine.replay_decision(archived, altered_input)

    # Must detect drift
    assert report.replayed_success is False
    assert report.input_hash_match is False
    assert "input_hash" in report.delta
