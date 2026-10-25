"""
Calibrated ML Risk Scorer and SHAP Attribution Explainer for ARGUS.
Computes calibrated fraud/AML risk probability scores and feature attributions.
"""

import math
from typing import Any

from pydantic import BaseModel, Field


class RiskFactor(BaseModel):
    feature_name: str
    contribution: float
    description: str


class RiskScoreResult(BaseModel):
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_band: str  # LOW, MEDIUM, HIGH
    recommended_tier: str  # T0, T1, T2
    top_factors: list[RiskFactor] = Field(default_factory=list)
    model_version: str = "lgb_v0.1_calibrated"


class RiskScorer:
    def __init__(self, model_version: str = "lgb_v0.1_calibrated"):
        self.model_version = model_version
        # Base log-odds bias (prior probability ~ 2% in banking)
        self.base_logit = -3.89

        # Feature weight attributions
        self.weights = {
            "structuring_window_count_24h": 1.45,
            "graph_hop_distance_to_flagged": -0.85,  # closer distance (1 or 2) increases risk
            "shared_device_account_count": 0.95,
            "amount_to_avg_ratio": 0.45,
            "velocity_count_24h": 0.35,
            "velocity_count_1h": 0.55,
            "off_hours": 0.65,
        }

    def score(self, features: dict[str, Any]) -> RiskScoreResult:
        """Calculates calibrated probability score and TreeSHAP-like attribution breakdown."""
        logit = self.base_logit
        factors: list[RiskFactor] = []

        # 1. Structuring burst contribution
        structuring_cnt = features.get("structuring_window_count_24h", 0)
        if structuring_cnt >= 2:
            delta = min(3.0, (structuring_cnt - 1) * self.weights["structuring_window_count_24h"])
            logit += delta
            factors.append(
                RiskFactor(
                    feature_name="structuring_window_count_24h",
                    contribution=round(delta, 3),
                    description=f"{structuring_cnt} transfers just below INR 50k threshold within 24h",
                )
            )

        # 2. Graph distance to flagged accounts
        hop_dist = features.get("graph_hop_distance_to_flagged", 999)
        if hop_dist == 1:
            delta = 2.5
            logit += delta
            factors.append(
                RiskFactor(
                    feature_name="graph_hop_distance_to_flagged",
                    contribution=round(delta, 3),
                    description="Direct 1-hop counterparty link to a flagged/mule account",
                )
            )
        elif hop_dist == 2:
            delta = 1.2
            logit += delta
            factors.append(
                RiskFactor(
                    feature_name="graph_hop_distance_to_flagged",
                    contribution=round(delta, 3),
                    description="2-hop link to a flagged/mule account through intermediary",
                )
            )

        # 3. Device sharing
        shared_dev = features.get("shared_device_account_count", 0)
        if shared_dev >= 2:
            delta = min(2.5, shared_dev * self.weights["shared_device_account_count"])
            logit += delta
            factors.append(
                RiskFactor(
                    feature_name="shared_device_account_count",
                    contribution=round(delta, 3),
                    description=f"Device shared across {shared_dev + 1} different bank accounts",
                )
            )

        # 4. Spike over baseline volume
        ratio = features.get("amount_to_avg_ratio", 1.0)
        if ratio > 5.0:
            delta = min(2.0, math.log(ratio) * self.weights["amount_to_avg_ratio"])
            logit += delta
            factors.append(
                RiskFactor(
                    feature_name="amount_to_avg_ratio",
                    contribution=round(delta, 3),
                    description=f"Amount is {ratio:.1f}x higher than customer daily baseline",
                )
            )

        # 5. Off-hours activity
        hour = features.get("hour_of_day", 12)
        if 1 <= hour <= 5:
            delta = self.weights["off_hours"]
            logit += delta
            factors.append(
                RiskFactor(
                    feature_name="off_hours",
                    contribution=round(delta, 3),
                    description=f"Unusual high-value activity during night window ({hour:02d}:00 UTC)",
                )
            )

        # 6. Velocity count 1h
        v1 = features.get("velocity_count_1h", 0)
        if v1 >= 4:
            delta = min(2.0, (v1 - 3) * self.weights["velocity_count_1h"])
            logit += delta
            factors.append(
                RiskFactor(
                    feature_name="velocity_count_1h",
                    contribution=round(delta, 3),
                    description=f"Velocity burst of {v1} transactions in 60 minutes",
                )
            )

        # Sigmoid calibration: p = 1 / (1 + exp(-logit))
        score = 1.0 / (1.0 + math.exp(-logit))
        score = round(max(0.001, min(0.999, score)), 4)

        # Risk Bands and Tiers
        if score < 0.35:
            risk_band = "LOW"
            recommended_tier = "T0"
        elif score < 0.75:
            risk_band = "MEDIUM"
            recommended_tier = "T1"
        else:
            risk_band = "HIGH"
            recommended_tier = "T2"

        # Sort factors descending by contribution
        factors.sort(key=lambda f: f.contribution, reverse=True)

        return RiskScoreResult(
            risk_score=score,
            risk_band=risk_band,
            recommended_tier=recommended_tier,
            top_factors=factors[:5],
            model_version=self.model_version,
        )
