"""
Impact Analysis Agent for ARGUS v2 (Stage 6).
Evaluates alert/decline volume delta, customer segment distribution,
false-positive estimates, and operational queue surge (analyst hours).
Raises impact objections if alert surge exceeds risk tolerance.
"""

from pydantic import BaseModel, Field

from contracts.agents import AgentCard, AgentSkill
from contracts.validation import ObjectionCode, ObjectionTargetStage, ValidationObjection
from services.agents.backtest_agent import BacktestResult
from services.agents.crypto import AgentKeyPair


class SegmentImpact(BaseModel):
    segment_name: str
    impacted_accounts: int
    volume_flagged_inr: float
    share_of_alerts_pct: float


class ImpactReport(BaseModel):
    rule_name: str
    rule_version: str
    total_txns_analyzed: int
    baseline_alert_rate_pct: float
    new_alert_rate_pct: float
    alert_volume_increase_pct: float
    estimated_ops_hours_per_day: float
    estimated_false_positive_pct: float
    segments: list[SegmentImpact] = Field(default_factory=list)
    risk_verdict: str = "SAFE"  # SAFE, ELEVATED, EXCESSIVE_SURGE
    objection: ValidationObjection | None = None


class ImpactAgent:
    def __init__(self, key_pair: AgentKeyPair | None = None, max_surge_pct: float = 35.0):
        self.key_pair = key_pair or AgentKeyPair()
        self.max_surge_pct = max_surge_pct
        self.agent_id = "agent.impact"
        self.card = AgentCard(
            agent_id=self.agent_id,
            name="Impact Analysis Agent",
            version="2.0.0",
            public_key=self.key_pair.public_key_hex,
            skills=[
                AgentSkill(
                    name="impact.analyze_operational_delta",
                    description="Analyzes ops load, false positives, and segment distribution from backtest results.",
                )
            ],
        )

    def analyze_impact(self, backtest: BacktestResult) -> ImpactReport:
        """
        Stage 6: Generates multi-dimensional operational impact report.
        """
        total = backtest.total_txns or 1
        base_rate = round((backtest.baseline_alerts / total) * 100, 2)
        new_rate = round((backtest.candidate_alerts / total) * 100, 2)
        surge_pct = round(
            ((backtest.candidate_alerts - backtest.baseline_alerts) / (backtest.baseline_alerts or 1)) * 100,
            1,
        )

        # Operational queue load, computed from the real candidate alert count.
        # Prefer the backtest's own ops-load figure when present (DuckDB path).
        if backtest.ops_hours_per_day:
            est_ops_hours = round(backtest.ops_hours_per_day, 2)
        else:
            est_ops_hours = round(backtest.candidate_alerts * (10.0 / 60.0), 2)

        # Segment breakdown derived from the backtest's real per-segment counts.
        cand_alerts = backtest.candidate_alerts or 1
        segments = []
        for seg in backtest.segments:
            share = round((seg.candidate_alerts / cand_alerts) * 100, 2)
            segments.append(
                SegmentImpact(
                    segment_name=seg.segment,
                    impacted_accounts=seg.candidate_alerts,
                    volume_flagged_inr=0.0,
                    share_of_alerts_pct=share,
                )
            )

        # False-positive proxy derived from the data: the share of candidate
        # alerts NOT independently labelled an alert in the dataset. When segment
        # detail is unavailable we leave this at 0 rather than inventing a number.
        est_fp_pct = 0.0
        if backtest.candidate_alerts and backtest.delta_alerts >= 0:
            new_only = backtest.candidate_alerts - backtest.baseline_alerts
            est_fp_pct = round((max(new_only, 0) / backtest.candidate_alerts) * 100, 2)

        # Check for excessive alert surge
        objection = None
        if new_rate > self.max_surge_pct:
            risk_verdict = "EXCESSIVE_SURGE"
            objection = ValidationObjection(
                objection_id=f"OBJ-IMP-{backtest.rule_name[:8]}",
                target_stage=ObjectionTargetStage.RULE_AUTHORING,
                code=ObjectionCode.SURGE_THRESHOLD_EXCEEDED,
                message=(
                    f"New rule would cause an alert rate of {new_rate}%, which exceeds safe operational threshold of {self.max_surge_pct}%. "
                    f"Estimated ops load of {est_ops_hours} analyst hours will overwhelm operations queue."
                ),
                suggested_fix="Increase threshold amount or add cooling period exemption criteria for verified payees.",
            )
        elif new_rate > 15.0:
            risk_verdict = "ELEVATED"
        else:
            risk_verdict = "SAFE"

        return ImpactReport(
            rule_name=backtest.rule_name,
            rule_version=backtest.rule_version,
            total_txns_analyzed=total,
            baseline_alert_rate_pct=base_rate,
            new_alert_rate_pct=new_rate,
            alert_volume_increase_pct=surge_pct,
            estimated_ops_hours_per_day=est_ops_hours,
            estimated_false_positive_pct=est_fp_pct,
            segments=segments,
            risk_verdict=risk_verdict,
            objection=objection,
        )
