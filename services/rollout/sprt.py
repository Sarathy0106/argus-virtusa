"""
Wald Sequential Probability Ratio Test (B8).

Compares the OBSERVED alert rate on the live canary stream against the rate the
backtest predicted. Each sampled transaction is a Bernoulli trial (alert / no
alert). We accumulate the log-likelihood ratio of:

  H1 (breach): true alert rate = p1  (meaningfully above the predicted rate)
  H0 (healthy): true alert rate = p0  (the backtest-predicted rate)

and stop when the LLR crosses the Wald bounds derived from the target error
rates (alpha, beta). This gives an early, statistically-grounded breach signal
without any magic threshold or forced flag.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class SPRTDecision:
    llr: float
    decision: str  # CONTINUE, ACCEPT_H1, ACCEPT_H0
    upper_bound: float
    lower_bound: float
    samples: int
    alerts: int


class WaldSPRT:
    def __init__(
        self,
        p0: float,
        p1: float,
        alpha: float = 0.05,
        beta: float = 0.05,
    ) -> None:
        # Clamp probabilities away from 0/1 so the log-likelihood terms are finite.
        self.p0 = min(max(p0, 1e-4), 1 - 1e-4)
        self.p1 = min(max(p1, 1e-4), 1 - 1e-4)
        if self.p1 <= self.p0:
            # Breach hypothesis must be a higher alert rate than healthy.
            self.p1 = min(self.p0 * 1.5 + 1e-3, 1 - 1e-4)
        self.alpha = alpha
        self.beta = beta
        # Wald decision boundaries on the LLR.
        self.upper = math.log((1 - beta) / alpha)
        self.lower = math.log(beta / (1 - alpha))
        self.llr = 0.0
        self.samples = 0
        self.alerts = 0
        self.decision = "CONTINUE"

    def update(self, is_alert: bool) -> SPRTDecision:
        """Feed one Bernoulli observation and return the current decision."""
        self.samples += 1
        if is_alert:
            self.alerts += 1
            self.llr += math.log(self.p1 / self.p0)
        else:
            self.llr += math.log((1 - self.p1) / (1 - self.p0))

        if self.decision == "CONTINUE":
            if self.llr >= self.upper:
                self.decision = "ACCEPT_H1"  # breach
            elif self.llr <= self.lower:
                self.decision = "ACCEPT_H0"  # healthy
        return self.snapshot()

    def update_batch(self, alerts: int, total: int) -> SPRTDecision:
        """Feed a batch of observations (alerts out of total)."""
        alerts = max(0, min(alerts, total))
        for _ in range(alerts):
            if self.decision == "CONTINUE":
                self.update(True)
        for _ in range(total - alerts):
            if self.decision == "CONTINUE":
                self.update(False)
        return self.snapshot()

    def snapshot(self) -> SPRTDecision:
        return SPRTDecision(
            llr=round(self.llr, 4),
            decision=self.decision,
            upper_bound=round(self.upper, 4),
            lower_bound=round(self.lower, 4),
            samples=self.samples,
            alerts=self.alerts,
        )
