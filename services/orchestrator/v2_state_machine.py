"""
Stateful Regulatory Rule Orchestrator for ARGUS v2.
Implements the full 10-stage gated pipeline:
Circular Intake -> Obligation Extraction & Applicability -> Policy Mapping
-> Rule Authoring -> Backtesting -> Impact Analysis -> Validation Gate
-> (Objection Loop with bounded iterations) -> Maker-Checker Approval
-> Shadow Deployment -> Canary Rollout & Automatic Rollback.
"""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from contracts.bank_profile import BankProfile, BankType, ProductType
from contracts.deployment import (
    CanaryMetrics,
    DeploymentStage,
    DualApprovalToken,
    RollbackRecord,
    ShadowEvaluation,
)
from contracts.memory import RegulationClause
from contracts.obligations import RegulatoryObligation
from contracts.policy_mapping import ConflictStatus, PolicyMappingResult
from contracts.rule_dsl import RuleDefinition
from contracts.transactions import Transaction
from contracts.validation import ObjectionTargetStage, ValidationObjection, ValidationReport
from services.agents.backtest_agent import BacktestAgent, BacktestResult
from services.agents.broker import CapabilityBroker
from services.agents.crypto import AgentKeyPair
from services.agents.deployment_agent import DeploymentAgent
from services.agents.impact_agent import ImpactAgent, ImpactReport
from services.agents.intake_agent import IntakeAgent
from services.agents.monitor_agent import MonitorAgent
from services.agents.obligation_agent import ObligationAgent
from services.agents.policy_mapper_agent import PolicyMapperAgent
from services.agents.rule_author_agent import RuleAuthorAgent
from services.agents.validator_agent import ValidatorAgent
from services.airlock.airlock import PIIAirlock
from services.ingest.simulator import SyntheticTransactionGenerator
from services.ledger.ledger import AuditLedger
from services.regcompiler.dsl_compiler import RuleDSLCompiler


class V2WorkflowState(BaseModel):
    circular_id: str
    circular_title: str
    raw_circular_text: str
    bank_profile: BankProfile
    current_stage: int = 1
    stage_name: str = "CIRCULAR_INTAKE"

    # Stage 1
    intake_result: dict[str, Any] = Field(default_factory=dict)
    clauses: list[RegulationClause] = Field(default_factory=list)

    # Stage 2
    obligations: list[RegulatoryObligation] = Field(default_factory=list)
    applicable_obligations: list[RegulatoryObligation] = Field(default_factory=list)

    # Stage 3
    policy_mapping: PolicyMappingResult | None = None

    # Stage 4
    rule_definition: RuleDefinition | None = None
    compiled_rego: str | None = None
    compiled_tests: str | None = None

    # Stage 5
    backtest_result: BacktestResult | None = None

    # Stage 6
    impact_report: ImpactReport | None = None

    # Stage 7
    validation_report: ValidationReport | None = None
    objection_history: list[ValidationObjection] = Field(default_factory=list)
    iteration_count: int = 1
    max_iterations: int = 3

    # Stage 8
    approval_token: DualApprovalToken | None = None
    approval_status: str = "PENDING"  # PENDING, APPROVED, REJECTED

    # Stage 9
    shadow_evaluation: ShadowEvaluation | None = None

    # Stage 10
    canary_metrics: list[CanaryMetrics] = Field(default_factory=list)
    rollback_record: RollbackRecord | None = None
    deployment_stage: DeploymentStage = DeploymentStage.DRAFT

    # Traceability Graph
    traceability_graph: dict[str, Any] = Field(default_factory=dict)
    audit_hashes: list[str] = Field(default_factory=list)


class RegulatoryRuleOrchestrator:
    def __init__(
        self,
        broker: CapabilityBroker | None = None,
        audit_ledger: AuditLedger | None = None,
        airlock: PIIAirlock | None = None,
        compiler: RuleDSLCompiler | None = None,
        deterministic: bool = True,
    ):
        self.deterministic = deterministic
        self.broker = broker or CapabilityBroker()
        self.audit_ledger = audit_ledger or AuditLedger()
        self.airlock = airlock or PIIAirlock()
        self.compiler = compiler or RuleDSLCompiler()

        # Initialize and register all 8 specialized agents with deterministic keys if enabled
        kp_intake = AgentKeyPair(seed="agent.intake") if deterministic else None
        kp_obl = AgentKeyPair(seed="agent.obligation") if deterministic else None
        kp_pol = AgentKeyPair(seed="agent.policy_mapper") if deterministic else None
        kp_rule = AgentKeyPair(seed="agent.rule_author") if deterministic else None
        kp_bt = AgentKeyPair(seed="agent.backtest") if deterministic else None
        kp_imp = AgentKeyPair(seed="agent.impact") if deterministic else None
        kp_val = AgentKeyPair(seed="agent.validator") if deterministic else None
        kp_dep = AgentKeyPair(seed="agent.deployment") if deterministic else None
        kp_mon = AgentKeyPair(seed="agent.monitor") if deterministic else None

        self.intake_agent = IntakeAgent(airlock=self.airlock, key_pair=kp_intake)
        self.obligation_agent = ObligationAgent(key_pair=kp_obl)
        self.policy_mapper_agent = PolicyMapperAgent(key_pair=kp_pol)
        self.rule_author_agent = RuleAuthorAgent(compiler=self.compiler, key_pair=kp_rule)
        self.backtest_agent = BacktestAgent(compiler=self.compiler, key_pair=kp_bt)
        self.impact_agent = ImpactAgent(key_pair=kp_imp)
        self.validator_agent = ValidatorAgent(compiler=self.compiler, key_pair=kp_val)
        self.deployment_agent = DeploymentAgent(
            audit_ledger=self.audit_ledger, compiler=self.compiler, key_pair=kp_dep
        )
        self.monitor_agent = MonitorAgent(
            deployment_agent=self.deployment_agent, audit_ledger=self.audit_ledger, key_pair=kp_mon
        )

        # Register cards in broker
        for agent in [
            self.intake_agent,
            self.obligation_agent,
            self.policy_mapper_agent,
            self.rule_author_agent,
            self.backtest_agent,
            self.impact_agent,
            self.validator_agent,
            self.deployment_agent,
            self.monitor_agent,
        ]:
            self.broker.register_agent(agent.card)

        self.ledger = self.audit_ledger
        self.state: V2WorkflowState | None = None
        self._maker_id: str = "maker_compliance_4492"

    def run_pipeline(
        self,
        circular_text: str | None = None,
        bank_profile: BankProfile | None = None,
        circular_id: str = "RBI-2024-118",
        circular_title: str = "Enhanced Risk Management for Immediate and UPI Transactions",
        historical_txns: list[Transaction] | None = None,
    ) -> V2WorkflowState:
        text = circular_text or SAMPLE_CIRCULAR_TEXT
        profile = bank_profile or SAMPLE_BANK_PROFILE
        if historical_txns is None:
            gen = SyntheticTransactionGenerator(seed=42)
            historical_txns = gen.generate_dataset(100)
        self.state = self.run_pipeline_to_approval(
            circular_id=circular_id,
            circular_title=circular_title,
            circular_text=text,
            bank_profile=profile,
            historical_txns=historical_txns,
        )
        return self.state

    def maker_signoff(self, maker_id: str = "maker_compliance_4492") -> None:
        self._maker_id = maker_id

    def checker_signoff(self, checker_id: str = "checker_risk_vp_9104") -> None:
        if self.state:
            self.grant_dual_approval(
                self.state,
                maker_id=self._maker_id,
                checker_id=checker_id,
            )

    def activate_shadow(self, live_txns: list[Transaction] | None = None) -> None:
        if self.state and self.state.approval_token:
            if live_txns is None:
                gen = SyntheticTransactionGenerator(seed=101)
                live_txns = gen.generate_dataset(50)
            self.execute_shadow_and_rollout(
                self.state,
                live_transactions=live_txns,
                force_canary_breach=False
            )

    def ramp_canary(self, traffic_pct: float = 10.0) -> None:
        if self.state and self.state.canary_metrics:
            self.state.canary_metrics[-1].traffic_pct = int(traffic_pct)

    def emergency_rollback(self, reason: str = "Emergency manual trigger") -> None:
        if self.state:
            rec = self.deployment_agent.execute_rollback(
                reason=reason,
                triggered_by="MANUAL_OPERATOR_OVERRIDE"
            )
            self.state.rollback_record = rec
            self.state.current_stage = DeploymentStage.ROLLED_BACK
            self.state.stage_name = "ROLLED_BACK"
            self._log_stage(
                self.state,
                "EMERGENCY_ROLLBACK_EXECUTED",
                {"reason": reason, "recovery_time_ms": rec.recovery_time_ms}
            )

    def run_pipeline_to_approval(
        self,
        circular_id: str,
        circular_title: str,
        circular_text: str,
        bank_profile: BankProfile,
        historical_txns: list[Transaction],
        simulate_objection_loop: bool = True,
    ) -> V2WorkflowState:
        """
        Executes Stages 1 through 7 (with Objection Loop), pausing at Stage 8 for Human Approval.
        """
        state = V2WorkflowState(
            circular_id=circular_id,
            circular_title=circular_title,
            raw_circular_text=circular_text,
            bank_profile=bank_profile,
        )

        # STAGE 1: Circular Intake
        state.current_stage = 1
        state.stage_name = "CIRCULAR_INTAKE"
        intake_res = self.intake_agent.process_circular(
            circular_id=circular_id,
            circular_title=circular_title,
            raw_text=circular_text,
        )
        state.intake_result = intake_res
        state.clauses = intake_res["clauses"]
        self._log_stage(state, "STAGE_1_INTAKE_COMPLETED", {"clauses": len(state.clauses)})

        # STAGE 2: Obligation Extraction & Applicability
        state.current_stage = 2
        state.stage_name = "OBLIGATION_EXTRACTION"
        obligations = self.obligation_agent.extract_obligations(
            clauses=state.clauses, bank_profile=bank_profile
        )
        state.obligations = obligations
        state.applicable_obligations = [
            o for o in obligations if o.applicability_status.value == "APPLICABLE"
        ]
        self._log_stage(
            state,
            "STAGE_2_OBLIGATIONS_EXTRACTED",
            {
                "total_obligations": len(obligations),
                "applicable_count": len(state.applicable_obligations),
            },
        )

        if not state.applicable_obligations:
            state.stage_name = "COMPLETED_NOT_APPLICABLE"
            return state

        target_obligation = state.applicable_obligations[0]

        # STAGE 3: Policy Mapping
        state.current_stage = 3
        state.stage_name = "POLICY_MAPPING"
        mapping_result = self.policy_mapper_agent.map_obligations(
            state.applicable_obligations, bank_id=bank_profile.bank_id
        )
        state.policy_mapping = mapping_result
        self._log_stage(
            state,
            "STAGE_3_POLICY_MAPPING_COMPLETED",
            {
                "unresolved_gaps": mapping_result.unresolved_gaps,
                "unresolved_conflicts": mapping_result.unresolved_conflicts,
            },
        )

        # OBJECTION LOOP (Stages 4, 5, 6, 7 with iterative resolution)
        target_mapping = mapping_result.mappings[0] if mapping_result.mappings else None
        active_objection: ValidationObjection | None = None

        while state.iteration_count <= state.max_iterations:
            # STAGE 4: Rule Authoring
            state.current_stage = 4
            state.stage_name = "RULE_AUTHORING"
            rule_def, rego, tests = self.rule_author_agent.author_rule(
                obligation=target_obligation,
                mapping=target_mapping,
                objection=active_objection,
                iteration=state.iteration_count if simulate_objection_loop else 2,
            )
            state.rule_definition = rule_def
            state.compiled_rego = rego
            state.compiled_tests = tests
            state.traceability_graph = self.compiler.build_traceability_graph(rule_def)

            # STAGE 5: Backtesting
            state.current_stage = 5
            state.stage_name = "BACKTESTING"
            backtest_res = self.backtest_agent.run_backtest(
                rule_def=rule_def, transactions=historical_txns
            )
            state.backtest_result = backtest_res

            # STAGE 6: Impact Analysis
            state.current_stage = 6
            state.stage_name = "IMPACT_ANALYSIS"
            impact_res = self.impact_agent.analyze_impact(backtest_res)
            state.impact_report = impact_res

            # STAGE 7: Validation Gate
            state.current_stage = 7
            state.stage_name = "VALIDATION"
            val_report = self.validator_agent.validate_draft_rule(
                rule_def=rule_def,
                mapping_result=state.policy_mapping,
                iteration=state.iteration_count,
            )
            state.validation_report = val_report

            if val_report.passed and (not impact_res.objection):
                self._log_stage(
                    state,
                    "STAGE_7_VALIDATION_PASSED",
                    {"certificate_id": val_report.certificate_id, "iteration": state.iteration_count},
                )
                break
            else:
                # OBJECTION DETECTED -> RE-ROUTE
                raised_objections = val_report.objections + (
                    [impact_res.objection] if impact_res.objection else []
                )
                active_objection = raised_objections[0]
                state.objection_history.append(active_objection)

                self._log_stage(
                    state,
                    "STAGE_7_OBJECTION_RAISED",
                    {
                        "code": active_objection.code.value,
                        "target_stage": active_objection.target_stage.value,
                        "iteration": state.iteration_count,
                        "message": active_objection.message,
                    },
                )

                # Re-route based on target_stage
                if active_objection.target_stage == ObjectionTargetStage.POLICY_MAPPING:
                    # Resolve conflict in policy mapper
                    if target_mapping:
                        self.policy_mapper_agent.resolve_mapping_conflict(
                            target_mapping, resolution_choice="LOWER_LIMIT_AND_ADD_COOLING"
                        )
                    state.policy_mapping.compute_summary()

                state.iteration_count += 1
                if state.iteration_count > state.max_iterations:
                    raise RuntimeError(
                        f"Objection loop exceeded maximum iterations ({state.max_iterations}). Halting for human intervention."
                    )

        # STAGE 8: Paused for Human Approval
        state.current_stage = 8
        state.stage_name = "HUMAN_APPROVAL_PENDING"
        return state

    def grant_dual_approval(
        self,
        state: V2WorkflowState,
        maker_id: str,
        checker_id: str,
    ) -> DualApprovalToken:
        """
        Stage 8: Maker-Checker dual human approval gate.
        Signs cryptographic approval token and unlocks live deployment.
        """
        if not state.validation_report or not state.validation_report.passed:
            raise PermissionError("Cannot approve rule that has not passed Stage 7 Validation.")

        if maker_id == checker_id:
            raise PermissionError("Dual approval strictly requires two distinct individuals.")

        rule_name = state.rule_definition.rule_name if state.rule_definition else "rule"
        version = state.rule_definition.version if state.rule_definition else "1.0.0"

        # Sign approvals using agent keys as proxies or human identity tokens
        maker_sig = self.intake_agent.key_pair.sign_payload({"maker": maker_id, "rule": rule_name})
        checker_sig = self.validator_agent.key_pair.sign_payload(
            {"checker": checker_id, "rule": rule_name}
        )

        token_id = (
            f"TOK-APP-{rule_name}-{maker_id[:5]}-{checker_id[:5]}"
            if self.deterministic
            else f"TOK-APP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        approved_at = (
            datetime(2026, 10, 26, 12, 15, 0, tzinfo=timezone.utc)
            if self.deterministic
            else datetime.now(timezone.utc)
        )
        token = DualApprovalToken(
            token_id=token_id,
            rule_name=rule_name,
            bundle_version=version,
            maker_id=maker_id,
            checker_id=checker_id,
            maker_signature=maker_sig,
            checker_signature=checker_sig,
            approved_at=approved_at,
        )

        state.approval_token = token
        state.approval_status = "APPROVED"
        self.deployment_agent.register_approval_token(token)

        self._log_stage(
            state,
            "STAGE_8_DUAL_APPROVAL_GRANTED",
            {"maker": maker_id, "checker": checker_id, "token_id": token.token_id},
        )
        return token

    def execute_shadow_and_rollout(
        self,
        state: V2WorkflowState,
        live_transactions: list[Transaction],
        force_canary_breach: bool = False,
    ) -> V2WorkflowState:
        """
        Executes Stages 9 and 10:
        Stage 9: Shadow deployment and concordance verification.
        Stage 10: Progressive canary ramp (1% -> 10% -> 50% -> 100%) and automatic rollback if breach occurs.
        """
        if not state.approval_token:
            raise PermissionError("Cannot deploy without verified Stage 8 approval token.")

        if not state.rule_definition:
            raise RuntimeError("No rule definition present to deploy.")

        # STAGE 9: Shadow Deployment
        state.current_stage = 9
        state.stage_name = "SHADOW_DEPLOYMENT"
        self.deployment_agent.deploy_to_shadow(
            state.rule_definition, state.approval_token.token_id
        )

        predicted_delta = (
            state.backtest_result.delta_percentage if state.backtest_result else 0.0
        )
        shadow_eval = self.deployment_agent.evaluate_shadow_stream(
            live_transactions=live_transactions,
            predicted_backtest_delta=predicted_delta,
        )
        state.shadow_evaluation = shadow_eval
        self._log_stage(
            state,
            "STAGE_9_SHADOW_EVALUATED",
            {
                "concordance": shadow_eval.concordance_percentage,
                "drift": shadow_eval.drift_from_backtest_pct,
                "within_tolerance": shadow_eval.within_tolerance,
            },
        )

        # STAGE 10: Rollout & Monitoring
        state.current_stage = 10
        state.stage_name = "ROLLOUT_AND_MONITORING"

        canary_stages = [
            (DeploymentStage.CANARY_1, 1),
            (DeploymentStage.CANARY_10, 10),
            (DeploymentStage.CANARY_50, 50),
            (DeploymentStage.PROMOTED_100, 100),
        ]

        for stage_enum, traffic_pct in canary_stages:
            self.deployment_agent.advance_canary_stage(stage_enum)
            state.deployment_stage = stage_enum

            # Sample metrics
            eval_count = int(len(live_transactions) * (traffic_pct / 100.0)) or 10
            alerts_count = int(eval_count * 0.04)  # 4% baseline alert rate
            declines_count = int(eval_count * 0.01)  # 1% decline rate
            latency_ms = 18.5 + (traffic_pct * 0.05)

            # Trigger breach at CANARY_50 if force_canary_breach is set
            should_breach = force_canary_breach and stage_enum == DeploymentStage.CANARY_50
            if should_breach:
                declines_count = int(eval_count * 0.08)  # 8% decline rate (breach > 5%)
                latency_ms = 85.0  # 85ms latency (breach > 50ms)

            metrics, rollback = self.monitor_agent.evaluate_metrics(
                stage=stage_enum,
                traffic_pct=traffic_pct,
                evaluations_count=eval_count,
                alerts_count=alerts_count,
                declines_count=declines_count,
                latency_p95_ms=latency_ms,
                force_breach=should_breach,
            )
            state.canary_metrics.append(metrics)

            if rollback:
                state.rollback_record = rollback
                state.deployment_stage = DeploymentStage.ROLLED_BACK
                state.stage_name = "AUTOMATIC_ROLLBACK_COMPLETED"
                self._log_stage(
                    state,
                    "STAGE_10_AUTOMATIC_ROLLBACK_TRIGGERED",
                    {
                        "reason": rollback.reason,
                        "recovery_time_ms": rollback.recovery_time_ms,
                        "active_version": rollback.to_version,
                    },
                )
                break
        else:
            state.stage_name = "PROMOTED_TO_PRODUCTION"

        return state

    def _log_stage(
        self, state: V2WorkflowState, event_type: str, payload: dict[str, Any]
    ) -> None:
        if self.deterministic:
            seq_num = len(self.audit_ledger._chain) + 1
            ts = datetime(2026, 10, 26, 12, 0, seq_num, tzinfo=timezone.utc)
            iso_ts = ts.isoformat()
        else:
            ts = None
            iso_ts = datetime.now(timezone.utc).isoformat()

        entry = self.audit_ledger.append(
            event_type=event_type,
            entity_id=state.circular_id,
            signer="orchestrator",
            payload={
                "current_stage": state.current_stage,
                "stage_name": state.stage_name,
                "timestamp": iso_ts,
                **payload,
            },
            recorded_at=ts,
        )
        state.audit_hashes.append(entry.entry_hash)


V2StateMachine = RegulatoryRuleOrchestrator

SAMPLE_CIRCULAR_TEXT = """Reserve Bank of India
Notification: RBI/2024-25/118
Master Direction – Enhanced Risk Management Framework for Immediate and UPI Transactions

Section 1: Scope and Applicability
These directions apply to all Scheduled Commercial Banks and Payment System Operators operating UPI channels.

Section 2: High-Value Immediate Transfer Velocity and Cooling Limits
All regulated entities shall enforce a mandatory cooling and step-up authentication rule for any retail immediate payment or UPI transaction where the single transaction amount meets or exceeds INR 50,000. During the velocity threshold breach, step-up multi-factor authentication is required.
Effective deadline: w.e.f 2025-01-01.

Section 3: Cross-Border Outflows
Cross-border RTGS payments for non-resident corporate entities shall be subject to pre-transaction screening and sanction list verification.
Effective deadline: w.e.f 2025-01-01.
"""

SAMPLE_BANK_PROFILE = BankProfile(
    bank_id="APEX_IN_001",
    bank_name="Argus Commercial Bank Ltd",
    bank_type=BankType.SCHEDULED_COMMERCIAL_BANK,
    licenses=["RETAIL_BANKING", "COMMERCIAL_BANKING", "PAYMENT_SYSTEM_OPERATOR"],
    active_products=[ProductType.UPI, ProductType.IMPS],
    supported_channels=["UPI", "MOBILE", "NET_BANKING"],
)

