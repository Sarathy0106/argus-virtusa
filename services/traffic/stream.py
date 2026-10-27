"""
Live traffic stream (B8).

Generates a seeded, reproducible stream of transactions sampled from the real
500k dataset, at a configurable rate, with mild drift over time. Shadow and each
canary step evaluate the candidate rule against this stream; metrics (alert rate,
decline rate, p95 latency) are MEASURED from the actual evaluation, never faked.

Chaos injectors (services/traffic/chaos.py) modify this stream — e.g. flooding it
with over-threshold transactions — so a breach emerges from real inputs.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PARQUET = REPO_ROOT / "data" / "parquet" / "transactions_500k.parquet"


@dataclass
class StreamTxn:
    amount: float
    channel: str
    is_cash: bool
    risk_band: str
    segment: str
    country: str
    mcc: str


@dataclass
class LiveTrafficStream:
    seed: int = 101
    parquet_path: Path = DEFAULT_PARQUET
    _pool: list[StreamTxn] = field(default_factory=list)
    _rng: random.Random = field(default_factory=lambda: random.Random(101))
    _tick: int = 0

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._load_pool()

    def _load_pool(self, pool_size: int = 5000) -> None:
        con = duckdb.connect()
        try:
            rows = con.execute(
                f"SELECT amount, channel, is_cash, risk_band, segment, country, mcc "
                f"FROM read_parquet('{self.parquet_path.as_posix()}') "
                f"USING SAMPLE {pool_size} ROWS (reservoir, {self.seed})"
            ).fetchall()
        finally:
            con.close()
        self._pool = [
            StreamTxn(
                amount=float(r[0]),
                channel=str(r[1]),
                is_cash=bool(r[2]),
                risk_band=str(r[3]),
                segment=str(r[4]),
                country=str(r[5]),
                mcc=str(r[6]),
            )
            for r in rows
        ]

    def sample(self, n: int) -> list[StreamTxn]:
        """Draw n transactions with mild time-based drift (amounts drift up a few
        percent as the stream progresses, simulating realistic load change)."""
        out: list[StreamTxn] = []
        for _ in range(n):
            base = self._rng.choice(self._pool)
            self._tick += 1
            drift = 1.0 + min(self._tick / 50000.0, 0.05)  # up to +5% drift
            out.append(
                StreamTxn(
                    amount=round(base.amount * drift, 2),
                    channel=base.channel,
                    is_cash=base.is_cash,
                    risk_band=base.risk_band,
                    segment=base.segment,
                    country=base.country,
                    mcc=base.mcc,
                )
            )
        return out
