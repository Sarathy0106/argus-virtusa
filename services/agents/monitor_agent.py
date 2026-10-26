"""
Monitor Agent for ARGUS v2 (Stage 10).
Performs real-time telemetry tracking during canary ramp:
evaluates decline rates, alert volumes, p95 latencies, and error rates.
Automatically triggers instantaneous rollback if safety thresholds are breached.
"""

from typing import Any

from contracts.agents import AgentCard, AgentSkill
from contracts.deployment import CanaryMetrics, DeploymentStage, RollbackRecord
from services.agents.crypto import AgentKeyPair
from services.agents.deployment_agent import DeploymentAgent
from services.ledger.ledger import AuditLedger


class MonitorAgent:
    def __init__(
        self,
        deployment_agent: DeploymentAgent,
        key_pair: AgentKeyPair | None = None,
        audit_ledger: AuditLedger | None = None,
        max_decline_rate_pct: float = 5.0,
        max_latency_p95_ms: float = 50.0,
        max_error_rate_pct: float = 0.5,
    ):
        self.deployment_agent = deployment_agent
        self.key_pair = key_pair or AgentKeyPair()
        self.audit_ledger = audit_ledger or AuditLedger()
        self.max_decline_rate_pct = max_decline_rate_pct
        self.max_latency_p95_ms = max_latency_p95_ms
        self.max_error_rate_pct = max_error_rate_pct

        self.agent_id = "agent.monitor"
        self.card = AgentCard(
            agent_id=self.agent_id,
            name="Rollout Telemetry & Drift Monitor Agent",
            version="2.0.0",
            public_key=self.key_pair.public_key_hex,
            skills=[
                AgentSkill(
                    name="monitor.evaluate_canary_telemetry",
                    description="Monitors live canary metrics and executes automatic rollback on breach.",
                )
            ],
        )
        self.metrics_history: list[CanaryMetrics] = []

    def evaluate_metrics(
        self,
        stage: DeploymentStage,
        traffic_pct: int,
        evaluations_count: int,
        alerts_count: int,
        declines_count: int,
        latency_p95_ms: float,
        errors_count: int = 0,
        force_breach: bool = False,
    ) -> tuple[CanaryMetrics, RollbackRecord | None]:
        """
        Stage 10: Continuously checks canary telemetry against safety thresholds.
        If threshold breach occurs, immediately triggers automatic rollback via DeploymentAgent.
        """
        alert_rate = round((alerts_count / (evaluations_count or 1)) * 100, 2)
        decline_rate = round((declines_count / (evaluations_count or 1)) * 100, 2)
        error_rate = round((errors_count / (evaluations_count or 1)) * 100, 3)

        breach = False
        breach_reason = None

        if force_breach:
            breach = True
            breach_reason = "FORCED_SAFETY_DRIFT_BREACH: Simulated spike in false-positive declines and p95 latency."
        elif decline_rate > self.max_decline_rate_pct:
            breach = True
            breach_reason = f"Decline rate of {decline_rate}% exceeded safety threshold of {self.max_decline_rate_pct}%."
        elif latency_p95_ms > self.max_latency_p95_ms:
            breach = True
            breach_reason = f"p95 latency of {latency_p95_ms}ms exceeded budget of {self.max_latency_p95_ms}ms."
        elif error_rate > self.max_error_rate_pct:
            breach = True
            breach_reason = f"Execution error rate of {error_rate}% exceeded budget of {self.max_error_rate_pct}%."

        metrics = CanaryMetrics(
            stage=stage,
            traffic_pct=traffic_pct,
            evaluations_count=evaluations_count,
            alerts_count=alerts_count,
            alert_rate_pct=alert_rate,
            decline_rate_pct=decline_rate,
            latency_p95_ms=latency_p95_ms,
            error_rate_pct=error_rate,
            breach_detected=breach,
            breach_reason=breach_reason,
        )
        self.metrics_history.append(metrics)

        rollback_record = None
        if breach:
            # TRIGGER AUTOMATIC ROLLBACK IMMEDIATELY
            rollback_record = self.deployment_agent.execute_rollback(
                reason=breach_reason or "Automated safety threshold breach",
                triggered_by="AUTOMATIC_BREACH",
            )

        return metrics, rollback_record
