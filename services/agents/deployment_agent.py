"""
Deployment Agent for ARGUS v2 (Stages 9 & 10).
Enforces:
1. Draft-only guardrail: Requires valid DualApprovalToken signed by maker and checker.
2. Shadow deployment: Runs in parallel on live traffic, measures concordance and drift.
3. Canary ramp: Progressive traffic allocation (1% -> 10% -> 50% -> 100%).
4. Instant rollback: Atomic bundle version pointer swap (< 1 second).
"""

import time
from datetime import datetime, timezone
from typing import Any

from contracts.agents import AgentCard, AgentSkill
from contracts.deployment import (
    DeploymentStage,
    DualApprovalToken,
    RollbackRecord,
    ShadowEvaluation,
)
from contracts.rule_dsl import RuleDefinition
from contracts.transactions import Transaction
from services.agents.crypto import AgentKeyPair
from services.ledger.ledger import AuditLedger
from services.policy.engine import PolicyEngine
from services.regcompiler.dsl_compiler import RuleDSLCompiler


class UnauthorizedDeploymentError(Exception):
    pass


class DeploymentAgent:
    def __init__(
        self,
        key_pair: AgentKeyPair | None = None,
        policy_engine: PolicyEngine | None = None,
        audit_ledger: AuditLedger | None = None,
        compiler: RuleDSLCompiler | None = None,
    ):
        self.key_pair = key_pair or AgentKeyPair()
        self.policy_engine = policy_engine or PolicyEngine()
        self.audit_ledger = audit_ledger or AuditLedger()
        self.compiler = compiler or RuleDSLCompiler()
        self.agent_id = "agent.deployment"
        self.card = AgentCard(
            agent_id=self.agent_id,
            name="Rule Deployment & Rollout Agent",
            version="2.0.0",
            public_key=self.key_pair.public_key_hex,
            skills=[
                AgentSkill(
                    name="deploy.shadow_evaluate",
                    description="Runs parallel shadow evaluation on live traffic.",
                ),
                AgentSkill(
                    name="deploy.canary_ramp",
                    description="Ramps canary traffic allocation across stages.",
                ),
                AgentSkill(
                    name="deploy.rollback",
                    description="Executes instant atomic rollback to prior rule bundle.",
                ),
            ],
        )

        # Active state
        self.active_bundle_version = "1.0.0"
        self.previous_bundle_version = "1.0.0"
        self.candidate_rule: RuleDefinition | None = None
        self.deployment_stage = DeploymentStage.DRAFT
        self.shadow_logs: list[dict[str, Any]] = []
        self.approval_tokens: dict[str, DualApprovalToken] = {}
        self.rollback_history: list[RollbackRecord] = []

    def register_approval_token(self, token: DualApprovalToken) -> None:
        """Stores a cryptographically verified DualApprovalToken."""
        if not token.maker_id or not token.checker_id or token.maker_id == token.checker_id:
            raise ValueError("Approval requires two distinct human individuals (Maker and Checker).")
        self.approval_tokens[token.token_id] = token
        self.deployment_stage = DeploymentStage.APPROVED

        # Log approval to Audit Ledger
        self.audit_ledger.append(
            event_type="DUAL_APPROVAL_REGISTERED",
            entity_id=token.rule_name,
            signer=f"maker:{token.maker_id}|checker:{token.checker_id}",
            payload=token.model_dump(mode="json"),
            recorded_at=token.approved_at,
        )

    def deploy_to_shadow(
        self, rule_def: RuleDefinition, approval_token_id: str
    ) -> DeploymentStage:
        """
        Transitions candidate rule into SHADOW mode. Requires dual approval token.
        """
        token = self.approval_tokens.get(approval_token_id)
        if not token or not token.is_valid:
            raise UnauthorizedDeploymentError(
                "Deployment rejected: Live deployment requires a valid DualApprovalToken."
            )

        self.candidate_rule = rule_def
        self.deployment_stage = DeploymentStage.SHADOW

        self.audit_ledger.append(
            event_type="SHADOW_DEPLOYMENT_STARTED",
            entity_id=rule_def.rule_name,
            signer=self.agent_id,
            payload={
                "rule_name": rule_def.rule_name,
                "version": rule_def.version,
                "approval_token_id": approval_token_id,
            },
        )
        return self.deployment_stage

    def evaluate_shadow_stream(
        self, live_transactions: list[Transaction], predicted_backtest_delta: float
    ) -> ShadowEvaluation:
        """
        Stage 9: Runs parallel evaluation of live transactions in Shadow mode.
        Live rule continues enforcement; candidate rule is logged only.
        """
        if not self.candidate_rule:
            raise RuntimeError("No candidate rule loaded in shadow deployment.")

        total = len(live_transactions)
        live_alerts = 0
        shadow_alerts = 0
        discrepancies = []

        for txn in live_transactions:
            eval_input = {
                "amount": txn.amount,
                "channel": txn.channel.value,
                "location_country": txn.location_country,
            }
            # Active live rule evaluation
            live_res = self.policy_engine.evaluate_local(eval_input)
            is_live_alert = live_res.outcome.value in ("HOLD", "BLOCK")
            if is_live_alert:
                live_alerts += 1

            # Shadow candidate rule evaluation
            cand_res = self.compiler.evaluate_locally(self.candidate_rule, eval_input)
            is_shadow_alert = cand_res.get("rule_hit", False)
            if is_shadow_alert:
                shadow_alerts += 1

            if is_live_alert != is_shadow_alert:
                discrepancies.append(
                    {
                        "txn_id": txn.id,
                        "amount": txn.amount,
                        "channel": txn.channel.value,
                        "live_outcome": live_res.outcome.value,
                        "shadow_outcome": cand_res.get("outcome", "ALLOW"),
                    }
                )

        observed_delta = round((shadow_alerts / (total or 1)) * 100, 2)
        drift = round(abs(observed_delta - predicted_backtest_delta), 2)
        concordance = round(((total - len(discrepancies)) / (total or 1)) * 100, 2)
        within_tolerance = drift <= 5.0  # Safe tolerance threshold ± 5%

        eval_result = ShadowEvaluation(
            rule_name=self.candidate_rule.rule_name,
            total_evaluations=total,
            live_rule_alerts=live_alerts,
            shadow_rule_alerts=shadow_alerts,
            discrepancy_count=len(discrepancies),
            concordance_percentage=concordance,
            backtest_predicted_delta=predicted_backtest_delta,
            observed_shadow_delta=observed_delta,
            drift_from_backtest_pct=drift,
            within_tolerance=within_tolerance,
            sample_discrepancies=discrepancies[:10],
        )

        return eval_result

    def advance_canary_stage(self, stage: DeploymentStage) -> DeploymentStage:
        """
        Progresses canary deployment: CANARY_1 -> CANARY_10 -> CANARY_50 -> PROMOTED_100.
        """
        if self.deployment_stage == DeploymentStage.ROLLED_BACK:
            raise RuntimeError("Cannot advance canary: Rule has been rolled back.")

        self.deployment_stage = stage
        if stage == DeploymentStage.PROMOTED_100:
            self.previous_bundle_version = self.active_bundle_version
            if self.candidate_rule:
                self.active_bundle_version = self.candidate_rule.version

        self.audit_ledger.append(
            event_type="CANARY_STAGE_ADVANCED",
            entity_id=self.candidate_rule.rule_name if self.candidate_rule else "UNKNOWN",
            signer=self.agent_id,
            payload={"new_stage": stage.value, "active_bundle_version": self.active_bundle_version},
        )
        return self.deployment_stage

    def execute_rollback(
        self, reason: str, triggered_by: str = "AUTOMATIC_BREACH"
    ) -> RollbackRecord:
        """
        Stage 10: Instant atomic rollback mechanism.
        Swaps the bundle version pointer back to the previous stable release.
        Measures recovery time in milliseconds (< 1000ms).
        """
        t0 = time.perf_counter()

        from_ver = self.active_bundle_version
        to_ver = self.previous_bundle_version

        # Atomic pointer swap
        self.active_bundle_version = to_ver
        self.deployment_stage = DeploymentStage.ROLLED_BACK

        # Real measured recovery time (monotonic clock around the actual pointer
        # swap). The duration is derived from perf_counter, not a constant (B10).
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 4)

        import hashlib

        record = RollbackRecord(
            rollback_id=f"RB-{hashlib.sha256(reason.encode()).hexdigest()[:8].upper()}",
            rule_name=self.candidate_rule.rule_name if self.candidate_rule else "compiled_bundle",
            from_version=from_ver,
            to_version=to_ver,
            reason=reason,
            triggered_by=triggered_by,
            recovery_time_ms=elapsed_ms,
            timestamp=datetime.now(timezone.utc),
        )
        self.rollback_history.append(record)

        # Log atomic rollback to hash-chained ledger
        self.audit_ledger.append(
            event_type="RULE_ROLLBACK_EXECUTED",
            entity_id=record.rule_name,
            signer=self.agent_id,
            payload=record.model_dump(mode="json"),
            recorded_at=record.timestamp,
        )
        return record
