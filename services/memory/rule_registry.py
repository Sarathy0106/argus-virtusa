"""
Bitemporal rule registry (B12).

Tracks rule versions with both valid-time (when the rule is effective in the real
world) and record-time (when the bank knew about it). An as-of query answers
"which rule version was live on date D, given what we knew at known_at?".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone


@dataclass
class RuleVersionRecord:
    rule_id: str
    version: str
    valid_from: date
    valid_to: date | None  # None = open-ended
    recorded_at: datetime
    clause_id: str | None = None
    note: str = ""


@dataclass
class BitemporalRuleRegistry:
    _records: list[RuleVersionRecord] = field(default_factory=list)

    def record_version(
        self,
        rule_id: str,
        version: str,
        valid_from: date,
        valid_to: date | None = None,
        clause_id: str | None = None,
        recorded_at: datetime | None = None,
        note: str = "",
    ) -> RuleVersionRecord:
        rec = RuleVersionRecord(
            rule_id=rule_id,
            version=version,
            valid_from=valid_from,
            valid_to=valid_to,
            recorded_at=recorded_at or datetime.now(timezone.utc),
            clause_id=clause_id,
            note=note,
        )
        self._records.append(rec)
        return rec

    def as_of(
        self, rule_id: str, on_date: date, known_at: datetime | None = None
    ) -> RuleVersionRecord | None:
        """Return the version of rule_id that was effective on `on_date` as known
        by `known_at` (record time). Among candidates, the latest-recorded wins."""
        known = known_at or datetime.now(timezone.utc)
        candidates = [
            r
            for r in self._records
            if r.rule_id == rule_id
            and r.recorded_at <= known
            and r.valid_from <= on_date
            and (r.valid_to is None or on_date <= r.valid_to)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.recorded_at)

    def seed_demo(self) -> None:
        """Seed the C3 UPI MCC-cap rule with a version boundary so an as-of query
        the day before its effective date returns the previous version (B12 gate).
        """
        if self._records:
            return
        self.record_version(
            rule_id="upi_high_risk_mcc_cap",
            version="1.0.0",
            valid_from=date(2024, 1, 1),
            valid_to=date(2026, 10, 31),
            clause_id="LEGACY",
            recorded_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            note="Pre-C3 baseline (no MCC cap).",
        )
        self.record_version(
            rule_id="upi_high_risk_mcc_cap",
            version="2.0.0",
            valid_from=date(2026, 11, 1),  # C3 effective date
            valid_to=None,
            clause_id="C3-2.1",
            recorded_at=datetime(2026, 10, 22, tzinfo=timezone.utc),
            note="C3: cap high-risk MCC 7995/6051 to INR 25,000/txn.",
        )
