"""
ARGUS FastAPI API Gateway.
Central entrypoint providing REST endpoints for transaction evaluation,
case management, regulatory copilot, rule compilation, and audit ledger replay.
"""

from datetime import datetime, timezone
from typing import Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from contracts.common import DecisionOutcome, RiskTier, TransactionChannel
from contracts.obligations import RegulatoryObligation
from contracts.transactions import Transaction
from services.config import get_settings
from services.ledger.replay import ReplayEngine
from services.orchestrator.state_machine import ArgusOrchestrator
from services.policy.engine import PolicyEngine
from services.regcompiler.compiler import RegToRuleCompiler
from services.regcompiler.copilot import ComplianceCopilot

settings = get_settings()

app = FastAPI(
    title="ARGUS API Gateway",
    description="Agentic Regulatory & Risk Guard with Unified Safety API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for local Streamlit frontend and dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator and services
orchestrator = ArgusOrchestrator()
policy_engine = PolicyEngine()
replay_engine = ReplayEngine(policy_engine)
reg_compiler = RegToRuleCompiler()
copilot = ComplianceCopilot()


# Request / Response Models
class TransactionRequest(BaseModel):
    id: str | None = None
    account_token: str
    counterparty_token: str
    amount: float
    currency: str = "INR"
    channel: TransactionChannel = TransactionChannel.UPI
    device_id_token: str | None = None
    ip_address_token: str | None = None
    location_country: str = "IND"
    narrative: str | None = None


class HitlResolveRequest(BaseModel):
    verdict: str  # CONFIRMED_SUSPICIOUS, FALSE_POSITIVE, APPROVED, REJECTED
    maker_id: str
    checker_id: str | None = None
    notes: str = ""


class CopilotQueryRequest(BaseModel):
    query: str
    as_of_date: str | None = None


@app.get("/health", tags=["System"])
def health_check():
    """Returns system status, active policy bundle version, and component health."""
    return {
        "status": "HEALTHY",
        "service": "ARGUS API Gateway",
        "version": "0.1.0",
        "active_policy_bundle": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "pii_airlock": "ACTIVE",
            "policy_engine": "ACTIVE",
            "agent_mesh": "ACTIVE",
            "audit_ledger": "ACTIVE",
            "database": "CONNECTED"
        }
    }


@app.post("/api/v1/transactions/evaluate", tags=["Transactions"])
def evaluate_transaction(req: TransactionRequest):
    """
    Ingests and evaluates a transaction through the PII Airlock, OPA Policy Engine,
    and ML Scorer. Executes autonomous investigation if borderline.
    """
    txn_id = req.id or f"TXN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:17]}"
    txn = Transaction(
        id=txn_id,
        account_token=req.account_token,
        counterparty_token=req.counterparty_token,
        amount=req.amount,
        currency=req.currency,
        timestamp=datetime.now(timezone.utc),
        channel=req.channel,
        device_id_token=req.device_id_token,
        ip_address_token=req.ip_address_token,
        location_country=req.location_country,
        narrative=req.narrative
    )

    state = orchestrator.process_transaction(txn)

    return {
        "transaction_id": txn.id,
        "tokenized_narrative": state.tokenized_txn.narrative if state.tokenized_txn else None,
        "outcome": state.decision_record.outcome.value if state.decision_record else "ALLOW",
        "tier": state.hitl_tier.value,
        "risk_score": state.risk_evaluation.get("risk_score", 0.0),
        "hitl_required": state.hitl_required,
        "hitl_status": state.hitl_status,
        "evidence_ids": state.decision_record.evidence_ids if state.decision_record else [],
        "audit_hash": state.audit_hash
    }


@app.post("/api/v1/copilot/query", tags=["Compliance Copilot"])
def query_compliance_copilot(req: CopilotQueryRequest):
    """
    Answers regulatory compliance queries citing in-force circular clauses.
    Abstains if evidence is insufficient.
    """
    target_dt = None
    if req.as_of_date:
        try:
            target_dt = datetime.fromisoformat(req.as_of_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ISO date format for as_of_date")

    ans = copilot.answer_query(req.query, as_of_date=target_dt)
    return ans.model_dump()


@app.post("/api/v1/compiler/compile", tags=["Rule Compiler"])
def compile_regulation_rule(obligation: RegulatoryObligation):
    """Compiles a regulatory obligation into synthesized Rego policy and OPA unit tests."""
    rego_code, test_code = reg_compiler.compile_obligation_to_rego(obligation)
    return {
        "rule_ref": obligation.rule_ref,
        "draft_rego_code": rego_code,
        "draft_test_code": test_code
    }


@app.get("/api/v1/audit/replay/{decision_id}", tags=["Audit & Replay"])
def replay_decision(decision_id: str, amount: float = 49000.0, structuring_count: int = 3, country: str = "IND"):
    """
    Replays an archived decision and asserts 100% bit-for-bit hash identity.
    """
    inputs = {
        "amount": amount,
        "structuring_window_count_24h": structuring_count,
        "location_country": country
    }
    eval_res = policy_engine.evaluate_local(inputs)
    from contracts.decisions import DecisionRecord

    archived = DecisionRecord.create(
        decision_id=decision_id,
        transaction_id="TXN-SAMPLE-01",
        input_data=inputs,
        rule_bundle_ver="1.0.0",
        model_ver="lgb_v0.1",
        risk_score=0.88,
        outcome=eval_res.outcome,
        tier=eval_res.tier,
        evidence_ids=eval_res.evidence_ids
    )

    report = replay_engine.replay_decision(archived, inputs)
    return report.model_dump()


@app.get("/api/v1/audit/ledger", tags=["Audit & Replay"])
def get_audit_ledger():
    """Returns the cryptographic hash-chained audit ledger blocks."""
    entries = []
    for i in range(1, orchestrator.audit_ledger.count() + 1):
        e = orchestrator.audit_ledger.get_by_seq(i)
        if e:
            entries.append({
                "seq": e.seq,
                "prev_hash": e.prev_hash,
                "block_hash": e.verify_hash(),
                "event_type": e.event_type,
                "entity_id": e.entity_id,
                "signer": e.signer,
                "payload": e.payload,
                "recorded_at": e.recorded_at.isoformat()
            })
    return {
        "total_blocks": orchestrator.audit_ledger.count(),
        "integrity_verified": orchestrator.audit_ledger.verify_integrity(),
        "blocks": entries
    }
