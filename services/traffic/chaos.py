"""
Chaos injectors (B9).

Chaos modifies the STREAM, not the results. `alert_flood` injects extra
over-threshold transactions, `latency_spike` adds artificial per-evaluation
delay, and `drift` shifts amounts upward. The breach that follows is produced by
the candidate rule evaluating these real (if adversarial) inputs — there is no
forced-breach flag anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from services.traffic.stream import LiveTrafficStream, StreamTxn


class ChaosKind(str, Enum):
    ALERT_FLOOD = "alert_flood"
    LATENCY_SPIKE = "latency_spike"
    DRIFT = "drift"


@dataclass
class ChaosController:
    stream: LiveTrafficStream
    active: set[ChaosKind] = field(default_factory=set)
    flood_multiplier: float = 3.0
    added_latency_ms: float = 60.0
    drift_factor: float = 1.6

    def inject(self, kind: ChaosKind) -> None:
        self.active.add(kind)

    def clear(self) -> None:
        self.active.clear()

    @property
    def latency_penalty_ms(self) -> float:
        return self.added_latency_ms if ChaosKind.LATENCY_SPIKE in self.active else 0.0

    def sample(self, n: int) -> list[StreamTxn]:
        """Return n stream transactions, mutated by whatever chaos is active."""
        txns = self.stream.sample(n)

        if ChaosKind.DRIFT in self.active:
            for t in txns:
                t.amount = round(t.amount * self.drift_factor, 2)

        if ChaosKind.ALERT_FLOOD in self.active:
            # Push a burst of clearly-over-threshold UPI transactions into the
            # batch (replace ~2/3 of it), so a threshold rule's alert rate climbs
            # well above the backtest-predicted rate.
            flood_count = min(len(txns), int(n * (self.flood_multiplier / (self.flood_multiplier + 1))))
            for i in range(flood_count):
                txns[i] = StreamTxn(
                    amount=250000.0,
                    channel="UPI",
                    is_cash=False,
                    risk_band="C",
                    segment="RETAIL",
                    country="IN",
                    mcc="7995",
                )
        return txns
