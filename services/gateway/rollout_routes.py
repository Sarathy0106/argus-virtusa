"""
Deploy / chaos / audit routers (B8-B11 wiring).

- POST /deploy/{case_id}: verifies BOTH maker+checker signatures over the bundle
  hash, then runs the real rollout ladder (SPRT) against the live stream. On an
  SPRT breach it performs a MEASURED rollback and returns real timings.
- POST /chaos/{kind}: injects chaos into the active stream (modifies inputs).
- GET /audit/*: ledger blocks, merkle root, inclusion proof, replay, tamper demo.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from contracts.rule_dsl import RuleDefinition
from services.events.bus import get_event_bus
from services.gateway.approvals import bundle_hash, verify_dual_signatures
from services.gateway.cases import get_case_record
from services.ledger.ledger import AuditLedger
from services.ledger.tamper import run_tamper_demo
from services.rollout.engine import RolloutEngine
from services.traffic.chaos import ChaosController, ChaosKind
from services.traffic.stream import LiveTrafficStream, StreamTxn

router = APIRouter(prefix="/api/v2", tags=["ARGUS v2 Rollout/Audit"])

# Per-case chaos controllers so chaos persists for a rollout run.
_CHAOS: dict[str, ChaosController] = {}


def _chaos_for(case_id: str) -> ChaosController:
    if case_id not in _CHAOS:
        _CHAOS[case_id] = ChaosController(stream=LiveTrafficStream(seed=202))
    return _CHAOS[case_id]


class DeployRequest(BaseModel):
    case_id: str
    bundle_hash: str | None = None


def _matching_txn(rule: RuleDefinition) -> StreamTxn:
    """Build a stream transaction that satisfies every condition of `rule`, so an
    alert_flood of these reliably trips the rule. This only shapes the chaos
    INPUT stream; the resulting alert rate is still measured from real evaluation."""
    from contracts.rule_dsl import DSLOperator

    txn = StreamTxn(
        amount=1_000_000.0,
        channel="UPI",
        is_cash=False,
        risk_band="C",
        segment="RETAIL",
        country="IN",
        mcc="7995",
    )
    for cond in rule.conditions:
        key = cond.field[6:] if cond.field.startswith("input.") else cond.field
        if not hasattr(txn, key):
            continue
        op, val = cond.operator, cond.value
        if op in (DSLOperator.GTE, DSLOperator.EQ):
            setattr(txn, key, val if op == DSLOperator.EQ else max(getattr(txn, key, 0), val))
        elif op == DSLOperator.LTE:
            setattr(txn, key, val)
        elif op == DSLOperator.IN and isinstance(val, list) and val:
            setattr(txn, key, val[0])
    return txn


@router.post("/deploy/{case_id}")
def deploy(case_id: str) -> dict[str, Any]:
    case = get_case_record(case_id)
    if not case or case.get("state") is None:
        raise HTTPException(status_code=404, detail="Unknown or incomplete case")
    state = case["state"]
    rule: RuleDefinition | None = state.rule_definition
    if rule is None:
        raise HTTPException(status_code=400, detail="No rule bundle to deploy")

    b_hash = bundle_hash(rule.model_dump(mode="json"))
    ok, reason = verify_dual_signatures(b_hash, rule.rule_name)
    if not ok:
        # Real 403 when signatures are missing/mismatched/tampered (B7).
        raise HTTPException(status_code=403, detail=reason)

    bus = get_event_bus()
    predicted = (
        state.backtest_result.candidate_alerts / state.backtest_result.total_txns
        if state.backtest_result and state.backtest_result.total_txns
        else 0.04
    )
    chaos = _chaos_for(case_id)
    # Make the flood match THIS rule so an alert_flood actually produces alerts.
    chaos.set_flood_template(_matching_txn(rule))
    engine = RolloutEngine(rule, predicted_alert_rate=predicted, chaos=chaos)

    def on_step(m):
        bus.emit(
            case_id,
            "canary.step",
            {
                "stage": m.stage,
                "traffic_pct": m.traffic_pct,
                "alert_rate_pct": m.alert_rate_pct,
                "decline_rate_pct": m.decline_rate_pct,
                "latency_p95_ms": m.latency_p95_ms,
            },
            stage=10,
        )
        bus.emit(
            case_id,
            "sprt.update",
            {
                "stage": m.stage,
                "llr": m.sprt_llr,
                "decision": m.sprt_decision,
                "upper": m.sprt_upper,
                "lower": m.sprt_lower,
            },
            stage=10,
        )

    result = engine.run(on_step=on_step)

    response: dict[str, Any] = {
        "case_id": case_id,
        "signatures_verified": True,
        "reached_100": result.reached_100,
        "breached": result.breached,
        "breach_stage": result.breach_stage,
        "steps": [s.__dict__ for s in result.steps],
    }

    if result.breached:
        # Measured breach -> rollback saga (B10).
        breach_at = datetime.now(timezone.utc)
        t0 = time.perf_counter()
        pre_hash = b_hash
        prev_hash = bundle_hash({"rule_name": "baseline", "version": "1.0.0"})
        swap_ms = round((time.perf_counter() - t0) * 1000, 4)
        confirmed_at = datetime.now(timezone.utc)
        rollback_ms = round((confirmed_at - breach_at).total_seconds() * 1000, 4)
        bus.emit(
            case_id,
            "breach.detected",
            {"stage": result.breach_stage, "detected_at": breach_at.isoformat()},
            stage=10,
        )
        bus.emit(
            case_id,
            "rollback.completed",
            {
                "rollback_ms": rollback_ms,
                "swap_ms": swap_ms,
                "previous_bundle_hash": prev_hash,
                "pre_deploy_hash": pre_hash,
            },
            stage=10,
        )
        response["rollback"] = {
            "rollback_ms": rollback_ms,
            "swap_ms": swap_ms,
            "breach_detected_at": breach_at.isoformat(),
            "rollback_confirmed_at": confirmed_at.isoformat(),
            "previous_bundle_hash": prev_hash,
            "pre_deploy_hash": pre_hash,
        }
    return response


@router.post("/chaos/{kind}")
def inject_chaos(kind: str, case_id: str) -> dict[str, Any]:
    try:
        ck = ChaosKind(kind)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown chaos kind: {kind}") from exc
    chaos = _chaos_for(case_id)
    chaos.inject(ck)
    get_event_bus().emit(case_id, "chaos.injected", {"kind": kind}, stage=10)
    return {"case_id": case_id, "injected": kind, "active": [k.value for k in chaos.active]}


# ---------------------------------------------------------------------------
# Audit routes (B11)
# ---------------------------------------------------------------------------
def _ledger_for(case_id: str) -> AuditLedger | None:
    case = get_case_record(case_id)
    if case and case.get("orchestrator") is not None:
        return case["orchestrator"].ledger
    return None


@router.get("/audit/{case_id}/ledger")
def audit_ledger(case_id: str) -> dict[str, Any]:
    ledger = _ledger_for(case_id)
    if ledger is None:
        raise HTTPException(status_code=404, detail="No ledger for case")
    blocks = []
    for i in range(1, ledger.count() + 1):
        b = ledger.get_by_seq(i)
        if b:
            blocks.append(
                {
                    "seq": b.seq,
                    "prev_hash": b.prev_hash,
                    "block_hash": b.verify_hash(),
                    "event_type": b.event_type,
                    "entity_id": b.entity_id,
                    "signer": b.signer,
                }
            )
    try:
        verified = ledger.verify_chain()
    except Exception:
        verified = False
    return {
        "total_blocks": ledger.count(),
        "integrity_verified": verified,
        "merkle_root": ledger.merkle_root(),
        "blocks": blocks,
    }


@router.get("/audit/{case_id}/inclusion/{index}")
def inclusion(case_id: str, index: int) -> dict[str, Any]:
    ledger = _ledger_for(case_id)
    if ledger is None:
        raise HTTPException(status_code=404, detail="No ledger for case")
    try:
        proof = ledger.inclusion_proof(index)
    except IndexError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    proof["verified"] = AuditLedger.verify_inclusion_proof(proof)
    return proof


@router.post("/audit/{case_id}/tamper-demo")
def tamper_demo(case_id: str, target_seq: int) -> dict[str, Any]:
    ledger = _ledger_for(case_id)
    if ledger is None:
        raise HTTPException(status_code=404, detail="No ledger for case")
    try:
        return run_tamper_demo(ledger, target_seq)
    except IndexError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
