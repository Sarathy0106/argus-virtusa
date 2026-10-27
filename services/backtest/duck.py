"""
Real backtest over the 500k transaction dataset using DuckDB (B5).

The draft rule and the current/baseline rule are evaluated over
`data/parquet/transactions_500k.parquet`. Every count returned here is produced
by a SQL aggregation over real rows — there are no constant deltas or multipliers.
Per-segment deltas and the ops-load estimate are computed from the row counts.

Progress is reported via a callback so the orchestrator can emit
`backtest.progress` events while chunks are scanned.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import duckdb
from pydantic import BaseModel, Field

from contracts.rule_dsl import DSLCondition, DSLOperator, RuleDefinition

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PARQUET = REPO_ROOT / "data" / "parquet" / "transactions_500k.parquet"

# DSL field names -> parquet column names. Only whitelisted columns can appear in
# a generated WHERE clause, which also prevents SQL injection via rule content.
FIELD_TO_COLUMN: dict[str, str] = {
    "amount": "amount",
    "channel": "channel",
    "is_cash": "is_cash",
    "risk_band": "risk_band",
    "country": "country",
    "mcc": "mcc",
    "segment": "segment",
    "currency": "currency",
}

# Minutes of analyst review per candidate alert (ops-load model). 10 minutes.
OPS_MINUTES_PER_ALERT = 10.0


class SegmentDelta(BaseModel):
    segment: str
    baseline_alerts: int
    candidate_alerts: int
    delta_alerts: int


class DuckBacktestResult(BaseModel):
    rule_name: str
    rule_version: str
    total_rows: int
    baseline_alerts: int
    candidate_alerts: int
    delta_alerts: int
    delta_percentage: float
    candidate_flagged_volume_inr: float
    ops_hours_per_day: float
    segments: list[SegmentDelta] = Field(default_factory=list)
    baseline_rule_name: str | None = None


class DuckBacktestError(Exception):
    pass


def _sql_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    # String: single-quote-escape.
    return "'" + str(value).replace("'", "''") + "'"


def _condition_to_sql(cond: DSLCondition) -> str:
    field = cond.field[6:] if cond.field.startswith("input.") else cond.field
    column = FIELD_TO_COLUMN.get(field)
    if column is None:
        # Unknown column cannot match any row — make it a hard FALSE so the rule
        # simply flags nothing rather than erroring.
        return "FALSE"
    op = cond.operator
    val = cond.value
    if op == DSLOperator.GTE:
        return f"{column} >= {_sql_literal(val)}"
    if op == DSLOperator.LTE:
        return f"{column} <= {_sql_literal(val)}"
    if op == DSLOperator.EQ:
        return f"{column} = {_sql_literal(val)}"
    if op == DSLOperator.NEQ:
        return f"{column} <> {_sql_literal(val)}"
    if op == DSLOperator.IN and isinstance(val, list):
        items = ", ".join(_sql_literal(v) for v in val)
        return f"{column} IN ({items})"
    if op == DSLOperator.NOT_IN and isinstance(val, list):
        items = ", ".join(_sql_literal(v) for v in val)
        return f"{column} NOT IN ({items})"
    return "FALSE"


def rule_to_where(rule: RuleDefinition | None) -> str:
    """Conjunction of all conditions. A rule with no conditions matches nothing."""
    if rule is None or not rule.conditions:
        return "FALSE"
    return " AND ".join(f"({_condition_to_sql(c)})" for c in rule.conditions)


class DuckBacktestEngine:
    def __init__(self, parquet_path: str | Path = DEFAULT_PARQUET) -> None:
        self.parquet_path = Path(parquet_path)
        if not self.parquet_path.exists():
            raise DuckBacktestError(f"Backtest dataset not found: {self.parquet_path}")

    def run(
        self,
        candidate: RuleDefinition,
        baseline: RuleDefinition | None = None,
        progress_cb: Callable[[int, int, int], None] | None = None,
        chunk_count: int = 10,
    ) -> DuckBacktestResult:
        """Evaluate candidate vs baseline over the full dataset.

        progress_cb(processed, total, running_candidate_alerts) is invoked
        `chunk_count` times as the scan progresses, so the UI gets real
        `backtest.progress` ticks derived from actual row scans.
        """
        con = duckdb.connect()
        try:
            rel = f"read_parquet('{self.parquet_path.as_posix()}')"
            total = con.execute(f"SELECT count(*) FROM {rel}").fetchone()[0]

            cand_where = rule_to_where(candidate)
            base_where = rule_to_where(baseline)

            # Real progressive scan: count candidate alerts over ordered chunks so
            # the running delta reported to the UI is measured, not simulated.
            running_alerts = 0
            if progress_cb is not None and total > 0:
                step = max(1, total // chunk_count)
                processed = 0
                while processed < total:
                    upper = min(processed + step, total)
                    chunk_alerts = con.execute(
                        f"SELECT count(*) FROM (SELECT *, row_number() OVER () AS rn FROM {rel}) "
                        f"WHERE rn > {processed} AND rn <= {upper} AND ({cand_where})"
                    ).fetchone()[0]
                    running_alerts += chunk_alerts
                    processed = upper
                    progress_cb(processed, total, running_alerts)

            baseline_alerts = con.execute(
                f"SELECT count(*) FROM {rel} WHERE {base_where}"
            ).fetchone()[0]
            candidate_alerts = con.execute(
                f"SELECT count(*) FROM {rel} WHERE {cand_where}"
            ).fetchone()[0]
            flagged_volume = con.execute(
                f"SELECT COALESCE(sum(amount), 0) FROM {rel} WHERE {cand_where}"
            ).fetchone()[0]

            # Per-segment baseline vs candidate counts, computed from rows.
            seg_rows = con.execute(
                f"""
                SELECT segment,
                       sum(CASE WHEN {base_where} THEN 1 ELSE 0 END) AS base_a,
                       sum(CASE WHEN {cand_where} THEN 1 ELSE 0 END) AS cand_a
                FROM {rel}
                GROUP BY segment
                ORDER BY cand_a DESC
                """
            ).fetchall()

            segments = [
                SegmentDelta(
                    segment=row[0],
                    baseline_alerts=int(row[1]),
                    candidate_alerts=int(row[2]),
                    delta_alerts=int(row[2]) - int(row[1]),
                )
                for row in seg_rows
            ]
        finally:
            con.close()

        delta = candidate_alerts - baseline_alerts
        delta_pct = round((delta / total) * 100, 4) if total else 0.0
        ops_hours = round((candidate_alerts * OPS_MINUTES_PER_ALERT) / 60.0, 2)

        return DuckBacktestResult(
            rule_name=candidate.rule_name,
            rule_version=candidate.version,
            total_rows=int(total),
            baseline_alerts=int(baseline_alerts),
            candidate_alerts=int(candidate_alerts),
            delta_alerts=int(delta),
            delta_percentage=delta_pct,
            candidate_flagged_volume_inr=round(float(flagged_volume), 2),
            ops_hours_per_day=ops_hours,
            segments=segments,
            baseline_rule_name=baseline.rule_name if baseline else None,
        )
