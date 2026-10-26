"""
API data client for ARGUS UI.
Tries the FastAPI gateway (http://localhost:8001) first.
If unreachable, silently falls back to seeded offline demo data.
"""
import json
import logging
import sys
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ui.data.seed import SEED_CASES, SEED_LEDGER, SEED_TRANSACTIONS

_API_BASE = "http://localhost:8001"
_TIMEOUT = 2.0
log = logging.getLogger(__name__)

_api_reachable: bool | None = None  # cached per-session


def _probe_api() -> bool:
    global _api_reachable
    if _api_reachable is not None:
        return _api_reachable
    try:
        r = httpx.get(f"{_API_BASE}/health", timeout=_TIMEOUT)
        _api_reachable = r.status_code == 200
    except Exception:
        _api_reachable = False
    return _api_reachable


def is_live() -> bool:
    return _probe_api()


def reset_probe() -> None:
    global _api_reachable
    _api_reachable = None


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------
def get_cases() -> list[dict[str, Any]]:
    if is_live():
        try:
            r = httpx.get(f"{_API_BASE}/cases", timeout=_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    return data
        except Exception as exc:
            log.warning("get_cases API failed: %s", exc)
    return SEED_CASES


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------
def get_ledger_blocks() -> list[dict[str, Any]]:
    if is_live():
        try:
            r = httpx.get(f"{_API_BASE}/audit/ledger", timeout=_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    return data
        except Exception as exc:
            log.warning("get_ledger_blocks API failed: %s", exc)
    return SEED_LEDGER


def append_ledger_block(event_type: str, entity_id: str, signer: str,
                         payload: dict) -> dict[str, Any] | None:
    if is_live():
        try:
            r = httpx.post(
                f"{_API_BASE}/audit/append",
                json={"event_type": event_type, "entity_id": entity_id,
                      "signer": signer, "payload": payload},
                timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                return r.json()
        except Exception as exc:
            log.warning("append_ledger_block API failed: %s", exc)
    # Offline: compute locally
    from ui.data.seed import _compute_block_hash, canonical_json_hash
    import hashlib
    from datetime import datetime, timezone

    import streamlit as st
    blocks = st.session_state.get("ledger_blocks", list(SEED_LEDGER))
    prev_hash = blocks[-1]["block_hash"] if blocks else "0" * 64
    recorded_at = datetime.now(timezone.utc).isoformat()
    block_hash = _compute_block_hash(
        prev_hash, payload, event_type, entity_id, signer, recorded_at
    )
    block = {
        "seq": len(blocks) + 1,
        "prev_hash": prev_hash,
        "block_hash": block_hash,
        "event_type": event_type,
        "entity_id": entity_id,
        "signer": signer,
        "payload": payload,
        "recorded_at": recorded_at,
    }
    blocks.append(block)
    st.session_state["ledger_blocks"] = blocks
    return block


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------
def get_transactions() -> list[dict[str, Any]]:
    return SEED_TRANSACTIONS


# ---------------------------------------------------------------------------
# Compliance query
# ---------------------------------------------------------------------------
def compliance_query(query: str, as_of_date) -> dict[str, Any]:
    if is_live():
        try:
            r = httpx.post(
                f"{_API_BASE}/compliance/query",
                json={"query": query, "as_of_date": as_of_date.isoformat()},
                timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                return r.json()
        except Exception as exc:
            log.warning("compliance_query API failed: %s", exc)
    # Offline: keyword match
    from ui.data.seed import REGULATION_CLAUSES
    from datetime import datetime, timezone
    q_lower = query.lower()
    as_of_dt = datetime.combine(as_of_date, datetime.min.time(), tzinfo=timezone.utc) if not isinstance(as_of_date, datetime) else as_of_date
    matched = []
    for clause in REGULATION_CLAUSES:
        if clause["valid_from"] <= as_of_dt <= clause["valid_to"]:
            if any(kw in q_lower for kw in clause.get("keywords", [])):
                matched.append(clause)
    if not matched:
        return {"abstained": True, "answer": "System Abstains: No in-force regulatory circular supports this inquiry.", "sources": []}
    sources = []
    answer_parts = []
    for c in matched:
        sources.append({
            "id": c["id"],
            "title": c["title"],
            "clause_ref": c["clause_ref"],
            "clause_text": c["clause_text"],
            "valid_from": c["valid_from"].isoformat(),
            "valid_to": c["valid_to"].isoformat(),
            "doc_id": c["doc_id"],
        })
        answer_parts.append(f"{c['clause_text']} [CLAUSE:{c['id']}]")
    answer = " ".join(answer_parts)
    return {"abstained": False, "answer": answer, "sources": sources}


# ---------------------------------------------------------------------------
# Rule compile + simulate
# ---------------------------------------------------------------------------
def compile_rule(obligation: dict) -> dict[str, Any]:
    if is_live():
        try:
            r = httpx.post(f"{_API_BASE}/rules/compile", json=obligation, timeout=_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception as exc:
            log.warning("compile_rule API failed: %s", exc)
    # Offline: generate rego locally (mirrors services/regcompiler/compiler.py)
    rule_name = obligation.get("rule_ref", "generated_rule").lower().replace("-", "_")
    threshold = obligation.get("condition_json", {}).get("threshold_amount", 50000)
    channel = obligation.get("condition_json", {}).get("channel", "UPI")
    action = obligation.get("action_json", {}).get("action", "HOLD")
    tier = obligation.get("action_json", {}).get("tier", "T1")
    rego = (
        f'package argus.compiled.{rule_name}\n\n'
        f'# Auto-compiled from Obligation: {obligation.get("id", "OBL-001")} (Clause: {obligation.get("clause_id", "N/A")})\n'
        f'version := "1.0.0"\n\n'
        f'rule_hit if {{\n'
        f'    input.amount >= {threshold}\n'
        f'    input.channel == "{channel}"\n'
        f'}}\n\n'
        f'decision := {{\n'
        f'    "action": "{action}",\n'
        f'    "tier": "{tier}",\n'
        f'    "evidence_id": "{rule_name}"\n'
        f'}} if rule_hit\n'
    )
    tests = (
        f'package argus.compiled.{rule_name}_test\n\n'
        f'test_rule_hit if {{\n'
        f'    rule_hit with input as {{\n'
        f'        "amount": {threshold + 1000},\n'
        f'        "channel": "{channel}"\n'
        f'    }}\n'
        f'}}\n\n'
        f'test_rule_miss if {{\n'
        f'    not rule_hit with input as {{\n'
        f'        "amount": {threshold - 1000},\n'
        f'        "channel": "{channel}"\n'
        f'    }}\n'
        f'}}\n'
    )
    return {"rego_code": rego, "test_code": tests}


def simulate_rule(obligation: dict, transactions: list[dict]) -> dict[str, Any]:
    if is_live():
        try:
            r = httpx.post(
                f"{_API_BASE}/rules/simulate",
                json={"obligation": obligation, "transactions": transactions},
                timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                return r.json()
        except Exception as exc:
            log.warning("simulate_rule API failed: %s", exc)
    # Offline simulation
    threshold = obligation.get("condition_json", {}).get("threshold_amount", 50000)
    channel = obligation.get("condition_json", {}).get("channel", "UPI")
    baseline = sum(1 for t in transactions if t["amount"] > 800000)
    triggered = [t for t in transactions if t["amount"] >= threshold and t["channel"] == channel]
    new_count = len(triggered)
    delta = round(((new_count - baseline) / max(baseline, 1)) * 100, 1)
    total_vol = round(sum(t["amount"] for t in triggered), 2)
    return {
        "total_txns_analyzed": len(transactions),
        "baseline_alert_count": baseline,
        "new_alert_count": new_count,
        "alert_increase_count": max(0, new_count - baseline),
        "delta_percentage": delta,
        "total_flagged_volume_inr": total_vol,
        "sample_triggered_ids": [t["id"] for t in triggered[:5]],
    }
