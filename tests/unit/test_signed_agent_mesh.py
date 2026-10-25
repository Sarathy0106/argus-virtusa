from datetime import datetime, timezone

import pytest

from contracts.agents import AgentCard, AgentMessage, AgentSkill
from services.agents.broker import CapabilityBroker
from services.agents.crypto import AgentKeyPair
from services.airlock.egress import PIILeakageError


def test_ed25519_sign_and_verify():
    keypair = AgentKeyPair()
    payload = {"account": "<ACCT_7F3A>", "risk_score": 0.88}
    sig = keypair.sign_payload(payload)

    # Valid verification
    assert AgentKeyPair.verify_signature(keypair.public_key_hex, sig, payload) is True

    # Tampered payload fails verification
    tampered_payload = {"account": "<ACCT_7F3A>", "risk_score": 0.12}
    assert AgentKeyPair.verify_signature(keypair.public_key_hex, sig, tampered_payload) is False


def test_capability_broker_dispatch_and_privacy_enforcement():
    broker = CapabilityBroker()
    agent_keys = AgentKeyPair()

    card = AgentCard(
        agent_id="agent.investigator",
        name="Investigator Agent",
        public_key=agent_keys.public_key_hex,
        skills=[AgentSkill(name="case.gather_evidence", description="Collects evidence")],
    )
    broker.register_agent(card)

    # 1. Valid signed tokenized call passes
    clean_payload = {"account_token": "<ACCT_7F3A>", "case_id": "CASE-101"}
    msg_id = "MSG-001"
    now = datetime.now(timezone.utc)
    signable_data = {
        "message_id": msg_id,
        "case_id": "CASE-101",
        "sender_id": "agent.investigator",
        "recipient_id": "agent.txn_risk",
        "skill": "case.gather_evidence",
        "payload": clean_payload,
        "timestamp": now.isoformat(),
    }
    sig = agent_keys.sign_payload(signable_data)

    msg = AgentMessage(
        message_id=msg_id,
        case_id="CASE-101",
        sender_id="agent.investigator",
        recipient_id="agent.txn_risk",
        skill="case.gather_evidence",
        payload=clean_payload,
        timestamp=now,
        signature=sig,
    )

    res = broker.dispatch(msg)
    assert res["status"] == "DISPATCHED"

    # 2. Privacy Violation: Attempting to pass raw PAN in payload is rejected!
    dirty_payload = {"account_token": "<ACCT_7F3A>", "pan_number": "ABCDE1234F"}
    dirty_signable = dict(signable_data, message_id="MSG-002", payload=dirty_payload)
    dirty_sig = agent_keys.sign_payload(dirty_signable)

    dirty_msg = AgentMessage(
        message_id="MSG-002",
        case_id="CASE-101",
        sender_id="agent.investigator",
        recipient_id="agent.txn_risk",
        skill="case.gather_evidence",
        payload=dirty_payload,
        timestamp=now,
        signature=dirty_sig,
    )

    with pytest.raises(PIILeakageError):
        broker.dispatch(dirty_msg)


def test_mcp_sanctions_tool():
    broker = CapabilityBroker()
    agent_keys = AgentKeyPair()
    card = AgentCard(
        agent_id="agent.kyc",
        name="KYC Agent",
        public_key=agent_keys.public_key_hex,
        skills=[AgentSkill(name="mcp.search_sanctions", description="Sanctions search")],
    )
    broker.register_agent(card)

    now = datetime.now(timezone.utc)
    payload = {"target": "VLADIMIR_PETROV"}
    signable = {
        "message_id": "MSG-MCP",
        "case_id": None,
        "sender_id": "agent.kyc",
        "recipient_id": "mcp.broker",
        "skill": "mcp.search_sanctions",
        "payload": payload,
        "timestamp": now.isoformat(),
    }
    sig = agent_keys.sign_payload(signable)

    msg = AgentMessage(
        message_id="MSG-MCP",
        sender_id="agent.kyc",
        recipient_id="mcp.broker",
        skill="mcp.search_sanctions",
        payload=payload,
        timestamp=now,
        signature=sig,
    )

    res = broker.dispatch(msg)
    assert res["match"] is True
    assert res["list_source"] == "OFAC_SDN_AND_UN_CONSOLIDATED"
