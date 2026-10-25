from datetime import datetime, timezone

import pytest

from contracts.common import DecisionOutcome, RiskTier, TransactionChannel
from contracts.transactions import Transaction
from services.orchestrator.state_machine import ArgusOrchestrator
from services.policy.engine import PolicyEvaluationResult


def test_orchestrator_routine_t0_auto_pass():
    orch = ArgusOrchestrator()
    routine_txn = Transaction(
        id="TXN-ROUTINE-01",
        account_token="<ACCT_GOOD_01>",
        counterparty_token="<ACCT_GOOD_02>",
        amount=1200.0,
        currency="INR",
        timestamp=datetime.now(timezone.utc),
        channel=TransactionChannel.UPI,
        narrative="Groceries at supermarket",
    )

    state = orch.process_transaction(routine_txn)

    # Must auto-pass without human intervention
    assert state.hitl_required is False
    assert state.hitl_status == "AUTO_PASSED"
    assert state.decision_record is not None
    assert state.decision_record.outcome == DecisionOutcome.ALLOW
    assert state.decision_record.tier == RiskTier.T0
    assert state.audit_hash is not None
    assert orch.audit_ledger.count() == 1


def test_orchestrator_borderline_t1_hitl_checkpoint():
    orch = ArgusOrchestrator()
    now = datetime.now(timezone.utc)

    # Ingest 2 structuring transactions first
    for i in range(2):
        prev = Transaction(
            id=f"TXN-PREV-{i}",
            account_token="<ACCT_STRUC>",
            counterparty_token="<ACCT_DEST>",
            amount=49000.0,
            timestamp=now,
            channel=TransactionChannel.UPI,
        )
        orch.txn_risk_agent.feature_pipeline.ingest_transaction(prev)

    # 3rd transaction hits structuring rule
    struc_txn = Transaction(
        id="TXN-STRUC-03",
        account_token="<ACCT_STRUC>",
        counterparty_token="<ACCT_DEST>",
        amount=49500.0,
        timestamp=now,
        channel=TransactionChannel.UPI,
        narrative="Consulting fee payment",
    )

    state = orch.process_transaction(struc_txn)

    # Must halt at HITL checkpoint
    assert state.hitl_required is True
    assert state.hitl_status == "PENDING"
    assert state.hitl_tier == RiskTier.T1
    assert state.decision_record is not None
    assert "aml_structuring_window" in state.decision_record.evidence_ids
    assert state.narrative["is_verified"] is True

    # Analyst Alice reviews and approves
    resolved = orch.resolve_hitl_checkpoint(
        state=state,
        analyst_verdict="CONFIRMED_SUSPICIOUS",
        maker_id="analyst_alice",
        analyst_notes="Structuring pattern confirmed across accounts.",
    )

    assert resolved.hitl_status == "CONFIRMED_SUSPICIOUS"
    assert resolved.maker == "analyst_alice"
    assert resolved.audit_hash is not None
    assert orch.audit_ledger.count() == 1


def test_orchestrator_t2_maker_checker_enforcement():
    orch = ArgusOrchestrator()
    # Rapid pass-through triggers T2
    mule_txn = Transaction(
        id="TXN-MULE-01",
        account_token="<MULE_ACC>",
        counterparty_token="<CASH_OUT>",
        amount=150000.0,
        timestamp=datetime.now(timezone.utc),
        channel=TransactionChannel.IMPS,
        metadata={"pattern_type": "MULE_OUTFLOW"},
    )
    # Feed mock inflow so rule triggers
    orch.txn_risk_agent.policy_engine.evaluate_local = lambda input_data: PolicyEvaluationResult(
        outcome=DecisionOutcome.HOLD,
        tier=RiskTier.T2,
        evidence_ids=["rapid_pass_through"],
        bundle_version="1.0.0",
    )

    state = orch.process_transaction(mule_txn)
    assert state.hitl_tier == RiskTier.T2

    # Attempting to resolve T2 with only Maker (no Checker) must be REJECTED
    with pytest.raises(PermissionError):
        orch.resolve_hitl_checkpoint(
            state=state, analyst_verdict="APPROVED", maker_id="analyst_alice", checker_id=None
        )

    # Resolving with both Maker and Checker succeeds
    resolved = orch.resolve_hitl_checkpoint(
        state=state,
        analyst_verdict="APPROVED",
        maker_id="analyst_alice",
        checker_id="senior_compliance_bob",
        analyst_notes="Reviewed and approved by senior compliance.",
    )
    assert resolved.checker == "senior_compliance_bob"
    assert resolved.audit_hash is not None
