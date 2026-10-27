"""
Memory router (B12) — bitemporal as-of queries for rule versions.

GET /memory/asof?rule_id=&date=&known_at= returns which rule version was live on
`date` given what the bank knew at `known_at`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Query

from services.memory.rule_registry import BitemporalRuleRegistry

router = APIRouter(prefix="/api/v2/memory", tags=["ARGUS v2 Memory"])

_REGISTRY = BitemporalRuleRegistry()
_REGISTRY.seed_demo()


@router.get("/asof")
def as_of(
    rule_id: str = Query(default="upi_high_risk_mcc_cap"),
    date_str: str = Query(alias="date"),
    known_at: str | None = Query(default=None),
) -> dict[str, Any]:
    on_date = date.fromisoformat(date_str)
    known = datetime.fromisoformat(known_at) if known_at else None
    rec = _REGISTRY.as_of(rule_id, on_date, known_at=known)
    if rec is None:
        return {"rule_id": rule_id, "date": date_str, "live_version": None}
    return {
        "rule_id": rule_id,
        "date": date_str,
        "known_at": known_at,
        "live_version": rec.version,
        "valid_from": rec.valid_from.isoformat(),
        "valid_to": rec.valid_to.isoformat() if rec.valid_to else None,
        "clause_id": rec.clause_id,
        "note": rec.note,
    }
