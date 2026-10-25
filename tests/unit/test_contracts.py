from datetime import datetime, timezone

from contracts.agents import AgentCard, AgentMessage, AgentSkill
from contracts.audit import AuditEntry
from contracts.common import DecisionOutcome, RiskTier, TransactionChannel
from contracts.decisions import DecisionRecord, canonical_json_hash
from contracts.memory import BitemporalFact
from contracts.transactions import Transaction


def test_transaction_contract_valid():
    txn = Transaction(
        id="TXN-001",
        account_token="<ACCT_1001>",
        counterparty_token="<ACCT_2002>",
        amount=49500.0,
        currency="INR",
        channel=TransactionChannel.UPI,
        narrative="Test transaction",
    )
    assert txn.id == "TXN-001"
    assert txn.amount == 49500.0
    assert txn.timestamp.tzinfo is not None
    assert txn.currency == "INR"


def test_canonical_json_hash_determinism():
    data1 = {"b": 2, "a": 1, "nested": {"y": "hello", "x": [1, 2, 3]}}
    data2 = {"nested": {"x": [1, 2, 3], "y": "hello"}, "a": 1, "b": 2}
    # Regardless of key ordering, the canonical hash must be identical
    hash1 = canonical_json_hash(data1)
    hash2 = canonical_json_hash(data2)
    assert hash1 == hash2


def test_decision_record_determinism():
    input_payload = {"amount": 49000.0, "channel": "UPI", "velocity_24h": 4, "sanctions_hit": False}

    record1 = DecisionRecord.create(
        decision_id="DEC-001",
        transaction_id="TXN-001",
        input_data=input_payload,
        rule_bundle_ver="v1.0.0",
        model_ver="lgb_v0.1",
        risk_score=0.85,
        outcome=DecisionOutcome.HOLD,
        tier=RiskTier.T1,
        evidence_ids=["aml_structuring_window"],
    )

    record2 = DecisionRecord.create(
        decision_id="DEC-002",
        transaction_id="TXN-001",
        input_data=input_payload,
        rule_bundle_ver="v1.0.0",
        model_ver="lgb_v0.1",
        risk_score=0.85,
        outcome=DecisionOutcome.HOLD,
        tier=RiskTier.T1,
        evidence_ids=["aml_structuring_window"],
    )

    # Identical inputs and decision logic must yield identical input_hash and output_hash
    assert record1.input_hash == record2.input_hash
    assert record1.output_hash == record2.output_hash


def test_audit_ledger_chaining():
    genesis_prev_hash = "0" * 64
    entry1 = AuditEntry.create(
        prev_hash=genesis_prev_hash,
        event_type="SYSTEM_INIT",
        entity_id="SYS-001",
        signer="admin",
        payload={"message": "System genesis initialization"},
    )
    hash1 = entry1.verify_hash()
    assert len(hash1) == 64

    entry2 = AuditEntry.create(
        prev_hash=hash1,
        event_type="DECISION_RECORDED",
        entity_id="DEC-001",
        signer="agent.txn_risk",
        payload={"verdict": "HOLD", "tier": "T1"},
    )
    assert entry2.prev_hash == hash1
    hash2 = entry2.verify_hash()
    assert hash1 != hash2


def test_bitemporal_fact_validity():
    now = datetime.now(timezone.utc)
    fact = BitemporalFact(
        subject="<ACCT_1001>",
        predicate="risk_category",
        object={"tier": "HIGH", "score": 0.92},
        valid_from=now,
        source="KYC_PORTAL",
    )
    assert fact.is_valid_at(now)
    assert fact.valid_to.year == 9999


def test_agent_card_and_message():
    skill = AgentSkill(
        name="risk.score_transaction",
        description="Calculates calibrated ML risk score and SHAP factors",
    )
    card = AgentCard(
        agent_id="agent.txn_risk",
        name="Transaction Risk Agent",
        public_key="abcd1234abcd1234",
        skills=[skill],
    )
    assert len(card.skills) == 1

    msg = AgentMessage(
        message_id="MSG-001",
        sender_id="agent.investigator",
        recipient_id="agent.txn_risk",
        skill="risk.score_transaction",
        payload={"account_token": "<ACCT_1001>"},
    )
    assert msg.skill == "risk.score_transaction"
