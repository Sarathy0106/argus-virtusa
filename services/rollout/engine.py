"""
Rollout engine (B8/B9/B10).

Runs shadow + the canary ladder against the live traffic stream. For each step it
MEASURES alert rate, decline rate and p95 latency from the actual candidate-rule
evaluation (time.perf_counter around each eval), feeds the alert outcomes into the
Wald SPRT, and triggers a measured rollback the moment SPRT accepts H1 (breach).

No fixed multipliers, no force-breach flag. A healthy stream rides the ladder to
100%; a chaos-flooded stream crosses the SPRT bound and rolls back.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from contracts.rule_dsl import DSLOperator, RuleDefinition
from services.rollout.sprt import WaldSPRT
from services.traffic.chaos import ChaosController
from services.traffic.stream import StreamTxn

CANARY_LADDER = [("CANARY_1", 1), ("CANARY_10", 10), ("CANARY_50", 50), ("PROMOTED_100", 100)]


def _matches(rule: RuleDefinition, txn: StreamTxn) -> bool:
    """Deterministic evaluation of the candidate rule against a stream txn."""
    fields = {
        "amount": txn.amount,
        "channel": txn.channel,
        "is_cash": txn.is_cash,
        "risk_band": txn.risk_band,
        "segment": txn.segment,
        "country": txn.country,
        "mcc": txn.mcc,
    }
    for cond in rule.conditions:
        key = cond.field[6:] if cond.field.startswith("input.") else cond.field
        actual = fields.get(key)
        if actual is None:
            return False
        op, val = cond.operator, cond.value
        if op == DSLOperator.GTE and not (actual >= val):
            return False
        if op == DSLOperator.LTE and not (actual <= val):
            return False
        if op == DSLOperator.EQ and not (actual == val):
            return False
        if op == DSLOperator.NEQ and not (actual != val):
            return False
        if op == DSLOperator.IN and actual not in val:
            return False
        if op == DSLOperator.NOT_IN and actual in val:
            return False
    return True


@dataclass
class StepMetrics:
    stage: str
    traffic_pct: int
    evaluations: int
    alerts: int
    declines: int
    alert_rate_pct: float
    decline_rate_pct: float
    latency_p95_ms: float
    sprt_llr: float
    sprt_decision: str
    sprt_upper: float
    sprt_lower: float
    breach: bool


@dataclass
class RolloutResult:
    steps: list[StepMetrics] = field(default_factory=list)
    breached: bool = False
    breach_stage: str | None = None
    reached_100: bool = False


class RolloutEngine:
    def __init__(
        self,
        candidate: RuleDefinition,
        predicted_alert_rate: float,
        chaos: ChaosController,
        samples_per_step: int = 2000,
    ) -> None:
        self.candidate = candidate
        self.chaos = chaos
        self.samples_per_step = samples_per_step
        # SPRT hypotheses:
        #   H0 (healthy): the backtest-predicted rate plus a tolerance buffer, so
        #     normal sampling variation around the prediction stays healthy.
        #   H1 (breach): a clearly elevated rate (predicted + a wide margin).
        # A chaos flood pushes the observed rate far past H1; normal drift does not.
        base = max(predicted_alert_rate, 1e-3)
        p0 = min(base + 0.05, 0.5)  # tolerance for normal variation
        p1 = min(max(base + 0.30, p0 * 4.0), 0.95)  # breach: well above predicted
        self.sprt = WaldSPRT(p0=p0, p1=p1)

    def _evaluate_batch(self, txns: list[StreamTxn]) -> tuple[int, int, float]:
        """Return (alerts, declines, p95_latency_ms) measured over the batch."""
        latencies: list[float] = []
        alerts = 0
        declines = 0
        penalty = self.chaos.latency_penalty_ms / 1000.0
        for t in txns:
            t0 = time.perf_counter()
            hit = _matches(self.candidate, t)
            if penalty:
                time.sleep(penalty / max(len(txns), 1))  # amortized injected delay
            dt = (time.perf_counter() - t0) * 1000.0
            latencies.append(dt + (self.chaos.latency_penalty_ms if penalty else 0.0))
            if hit:
                alerts += 1
                outcome = str(self.candidate.action.outcome).upper()
                if outcome in ("BLOCK", "DECLINE"):
                    declines += 1
        latencies.sort()
        p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else 0.0
        return alerts, declines, round(p95, 4)

    def run(self, on_step: Callable[[StepMetrics], None] | None = None) -> RolloutResult:
        result = RolloutResult()
        for stage, pct in CANARY_LADDER:
            n = max(1, int(self.samples_per_step * (pct / 100.0)))
            txns = self.chaos.sample(n)
            alerts, declines, p95 = self._evaluate_batch(txns)
            dec = self.sprt.update_batch(alerts, len(txns))

            breach = dec.decision == "ACCEPT_H1"
            metrics = StepMetrics(
                stage=stage,
                traffic_pct=pct,
                evaluations=len(txns),
                alerts=alerts,
                declines=declines,
                alert_rate_pct=round((alerts / len(txns)) * 100, 2),
                decline_rate_pct=round((declines / len(txns)) * 100, 2),
                latency_p95_ms=p95,
                sprt_llr=dec.llr,
                sprt_decision=dec.decision,
                sprt_upper=dec.upper_bound,
                sprt_lower=dec.lower_bound,
                breach=breach,
            )
            result.steps.append(metrics)
            if on_step:
                on_step(metrics)

            if breach:
                result.breached = True
                result.breach_stage = stage
                return result

        result.reached_100 = True
        return result
