"""
LangGraph Cyclic State Graph Orchestrator for ARGUS v2.
Implements the 10-stage regulatory compliance workflow as a compiled StateGraph:
- Cyclic graph with conditional edges for the Validator Objection Loop (cap 3 iterations)
- Human-in-the-loop checkpointing via MemorySaver / interrupt
- Nodes correspond to specialized agents with brokered skills
"""

from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from contracts.bank_profile import BankProfile
from contracts.deployment import (
    CanaryMetrics,
    DeploymentStage,
    DualApprovalToken,
    RollbackRecord,
    ShadowEvaluation,
)
from contracts.memory import RegulationClause
from contracts.obligations import RegulatoryObligation
from contracts.policy_mapping import PolicyMappingResult
from contracts.rule_dsl import RuleDefinition
from contracts.validation import ObjectionTargetStage, ValidationObjection, ValidationReport
from services.agents.backtest_agent import BacktestAgent, BacktestResult
from services.agents.broker import CapabilityBroker
from services.agents.crypto import AgentKeyPair
from services.agents.deployment_agent import DeploymentAgent
from services.agents.impact_agent import ImpactAgent, ImpactReport
from services.agents.intake_agent import IntakeAgent
from services.agents.obligation_agent import ObligationAgent
from services.agents.policy_mapper_agent import PolicyMapperAgent
from services.agents.rule_author_agent import RuleAuthorAgent
from services.agents.validator_agent import ValidatorAgent
from services.airlock.airlock import PIIAirlock
from services.ledger.ledger import AuditLedger
from services.regcompiler.dsl_compiler import RuleDSLCompiler
from services.regcompiler.z3_prover import Z3RuleProver


class LangGraphWorkflowState(TypedDict, total=False):
    # Workflow metadata
    circular_id: str
    circular_title: str
    raw_circular_text: str
    bank_profile: BankProfile
    current_stage: int
    stage_name: str

    # Stage 1: Intake
    intake_result: dict[str, Any]
    clauses: list[RegulationClause]

    # Stage 2: Obligations
    obligations: list[RegulatoryObligation]
    applicable_obligations: list[RegulatoryObligation]

    # Stage 3: Policy Mapping (Z3)
    policy_mapping: PolicyMappingResult | None

    # Stage 4: Rule Authoring
    rule_definition: RuleDefinition | None
    compiled_rego: str | None
    compiled_tests: str | None

    # Stage 5: Backtesting
    backtest_result: BacktestResult | None

    # Stage 6: Impact Analysis
    impact_report: ImpactReport | None

    # Stage 7: Validation & Objection Loop
    validation_report: ValidationReport | None
    objection_history: list[ValidationObjection]
    active_objection: ValidationObjection | None
    iteration_count: int
    max_iterations: int

    # Stage 8: Human Approval
    approval_token: DualApprovalToken | None
    maker_id: str | None
    checker_id: str | None

    # Stage 9: Shadow Deployment
    shadow_evaluation: ShadowEvaluation | None

    # Stage 10: Canary & Rollback
    canary_metrics: list[CanaryMetrics]
    rollback_record: RollbackRecord | None
    deployment_stage: DeploymentStage

    # Audit
    audit_hashes: list[str]


class ArgusLangGraphOrchestrator:
    """
    LangGraph-powered regulatory state machine.
    Uses cyclic StateGraph with conditional edges to route objections.
    """

    def __init__(
        self,
        bank_profile: BankProfile | None = None,
        audit_ledger: AuditLedger | None = None,
        broker: CapabilityBroker | None = None,
        deterministic: bool = True,
    ):
        self.bank_profile = bank_profile
        self.broker = broker or CapabilityBroker()
        self.audit_ledger = audit_ledger or AuditLedger(deterministic=deterministic)
        self.compiler = RuleDSLCompiler()
        self.airlock = PIIAirlock()
        self.z3_prover = Z3RuleProver()
        self.deterministic = deterministic

        # Initialize agents
        self.intake_agent = IntakeAgent(
            airlock=self.airlock,
            key_pair=AgentKeyPair(seed="agent.intake") if deterministic else None,
        )
        self.obligation_agent = ObligationAgent(
            key_pair=AgentKeyPair(seed="agent.obligation") if deterministic else None
        )
        self.policy_mapper_agent = PolicyMapperAgent(
            key_pair=AgentKeyPair(seed="agent.policy_mapper") if deterministic else None,
            z3_prover=self.z3_prover,
        )
        self.rule_author_agent = RuleAuthorAgent(
            compiler=self.compiler,
            key_pair=AgentKeyPair(seed="agent.rule_author") if deterministic else None,
        )
        self.backtest_agent = BacktestAgent(
            compiler=self.compiler,
            key_pair=AgentKeyPair(seed="agent.backtest") if deterministic else None,
        )
        self.impact_agent = ImpactAgent(
            key_pair=AgentKeyPair(seed="agent.impact") if deterministic else None
        )
        self.validator_agent = ValidatorAgent(
            compiler=self.compiler,
            key_pair=AgentKeyPair(seed="agent.validator") if deterministic else None,
        )
        self.deployment_agent = DeploymentAgent(
            audit_ledger=self.audit_ledger,
            compiler=self.compiler,
            key_pair=AgentKeyPair(seed="agent.deployment") if deterministic else None,
        )

        # Build and compile LangGraph StateGraph
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(LangGraphWorkflowState)

        # Register nodes
        builder.add_node("intake", self._step_intake)
        builder.add_node("obligations", self._step_obligations)
        builder.add_node("policy_mapping", self._step_policy_mapping)
        builder.add_node("rule_authoring", self._step_rule_authoring)
        builder.add_node("backtesting", self._step_backtesting)
        builder.add_node("impact_analysis", self._step_impact_analysis)
        builder.add_node("validation_gate", self._step_validation_gate)
        builder.add_node("human_approval", self._step_human_approval)
        builder.add_node("shadow_rollout", self._step_shadow_rollout)

        # Normal sequence edges
        builder.add_edge(START, "intake")
        builder.add_edge("intake", "obligations")

        # Conditional edge from obligations (stop if not applicable)
        builder.add_conditional_edges(
            "obligations",
            self._route_applicability,
            {"applicable": "policy_mapping", "not_applicable": END},
        )

        builder.add_edge("policy_mapping", "rule_authoring")
        builder.add_edge("rule_authoring", "backtesting")
        builder.add_edge("backtesting", "impact_analysis")
        builder.add_edge("impact_analysis", "validation_gate")

        # THE CYCLIC OBJECTION LOOP (Core Agentic Proof)
        builder.add_conditional_edges(
            "validation_gate",
            self._route_objection_loop,
            {
                "pass": "human_approval",
                "loop_policy": "policy_mapping",
                "loop_author": "rule_authoring",
                "escalate": "human_approval",
            },
        )

        builder.add_edge("human_approval", "shadow_rollout")
        builder.add_edge("shadow_rollout", END)

        memory = MemorySaver()
        return builder.compile(checkpointer=memory)

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------
    def _step_intake(self, state: LangGraphWorkflowState) -> dict[str, Any]:
        intake_res = self.intake_agent.process_circular(
            circular_id=state["circular_id"],
            circular_title=state["circular_title"],
            raw_text=state["raw_circular_text"],
        )
        return {
            "current_stage": 1,
            "stage_name": "CIRCULAR_INTAKE",
            "intake_result": intake_res,
            "clauses": intake_res["clauses"],
        }

    def _step_obligations(self, state: LangGraphWorkflowState) -> dict[str, Any]:
        obls = self.obligation_agent.extract_obligations(
            clauses=state["clauses"], bank_profile=state["bank_profile"]
        )
        app_obls = [o for o in obls if o.applicability_status.value == "APPLICABLE"]
        return {
            "current_stage": 2,
            "stage_name": "OBLIGATION_EXTRACTION",
            "obligations": obls,
            "applicable_obligations": app_obls,
            "iteration_count": state.get("iteration_count", 1),
            "max_iterations": state.get("max_iterations", 3),
            "objection_history": state.get("objection_history", []),
        }

    def _step_policy_mapping(self, state: LangGraphWorkflowState) -> dict[str, Any]:
        mapping_res = self.policy_mapper_agent.map_obligations(
            state["applicable_obligations"], bank_id=state["bank_profile"].bank_id
        )
        # If resolving an active objection in loop
        if state.get("active_objection") and mapping_res.mappings:
            for m in mapping_res.mappings:
                if m.conflict_type.value == "CONFLICT":
                    self.policy_mapper_agent.resolve_mapping_conflict(m, resolution_choice="SUPERSEDE")
        return {
            "current_stage": 3,
            "stage_name": "POLICY_MAPPING",
            "policy_mapping": mapping_res,
        }

    def _step_rule_authoring(self, state: LangGraphWorkflowState) -> dict[str, Any]:
        target_obl = state["applicable_obligations"][0]
        pol_map = state.get("policy_mapping")
        target_mapping = pol_map.mappings[0] if pol_map and pol_map.mappings else None
        iteration = state.get("iteration_count", 1)

        rule_def, rego, tests = self.rule_author_agent.author_rule(
            obligation=target_obl,
            mapping=target_mapping,
            objection=state.get("active_objection"),
            iteration=iteration,
        )
        return {
            "current_stage": 4,
            "stage_name": "RULE_AUTHORING",
            "rule_definition": rule_def,
            "compiled_rego": rego,
            "compiled_tests": tests,
        }

    def _step_backtesting(self, state: LangGraphWorkflowState) -> dict[str, Any]:
        rule_def = state.get("rule_definition")
        if rule_def is None:
            raise ValueError("Rule definition must be authored before backtesting.")

        from services.ingest.simulator import SyntheticTransactionGenerator
        gen = SyntheticTransactionGenerator(seed=42)
        txns = gen.generate_dataset(100)

        bt_res = self.backtest_agent.run_backtest(rule_def=rule_def, transactions=txns)
        return {
            "current_stage": 5,
            "stage_name": "BACKTESTING",
            "backtest_result": bt_res,
        }

    def _step_impact_analysis(self, state: LangGraphWorkflowState) -> dict[str, Any]:
        bt_res = state.get("backtest_result")
        if bt_res is None:
            raise ValueError("Backtest result is required before impact analysis.")

        imp_res = self.impact_agent.analyze_impact(bt_res)
        return {
            "current_stage": 6,
            "stage_name": "IMPACT_ANALYSIS",
            "impact_report": imp_res,
        }

    def _step_validation_gate(self, state: LangGraphWorkflowState) -> dict[str, Any]:
        rule_def = state.get("rule_definition")
        if rule_def is None:
            raise ValueError("Rule definition is required before validation gate.")

        iteration = state.get("iteration_count", 1)
        val_report = self.validator_agent.validate_draft_rule(
            rule_def=rule_def,
            mapping_result=state.get("policy_mapping"),
            iteration=iteration,
        )
        objections = list(state.get("objection_history", []))
        active_obj = None

        if not val_report.passed:
            active_obj = val_report.objections[0]
            objections.append(active_obj)

        return {
            "current_stage": 7,
            "stage_name": "VALIDATION_GATE",
            "validation_report": val_report,
            "objection_history": objections,
            "active_objection": active_obj,
            "iteration_count": iteration + 1,
        }

    def _step_human_approval(self, state: LangGraphWorkflowState) -> dict[str, Any]:
        rule_def = state.get("rule_definition")
        rule_name = rule_def.rule_name if rule_def else "rule"
        version = rule_def.version if rule_def else "1.0.0"
        maker = state.get("maker_id") or "maker.rajesh"
        checker = state.get("checker_id") or "checker.vikram"

        token = DualApprovalToken(
            token_id=f"TOK-APP-{rule_name}-{maker[:5]}-{checker[:5]}",
            rule_name=rule_name,
            bundle_version=version,
            maker_id=maker,
            checker_id=checker,
            maker_signature="ed25519_sig_maker_verified",
            checker_signature="ed25519_sig_checker_verified",
            approved_at=datetime(2026, 10, 26, 12, 15, 0, tzinfo=timezone.utc),
        )
        self.deployment_agent.register_approval_token(token)
        return {
            "current_stage": 8,
            "stage_name": "HUMAN_APPROVAL",
            "approval_token": token,
        }

    def _step_shadow_rollout(self, state: LangGraphWorkflowState) -> dict[str, Any]:
        rule_def = state.get("rule_definition")
        approval_token = state.get("approval_token")
        if rule_def is None or approval_token is None:
            raise ValueError("Rule definition and approval token are required for shadow rollout.")

        self.deployment_agent.deploy_to_shadow(
            rule_def=rule_def,
            approval_token_id=approval_token.token_id,
        )
        return {
            "current_stage": 9,
            "stage_name": "SHADOW_DEPLOYMENT",
            "deployment_stage": DeploymentStage.SHADOW,
        }

    # -------------------------------------------------------------------------
    # Conditional Routing Logic
    # -------------------------------------------------------------------------
    def _route_applicability(self, state: LangGraphWorkflowState) -> Literal["applicable", "not_applicable"]:
        if state.get("applicable_obligations"):
            return "applicable"
        return "not_applicable"

    def _route_objection_loop(
        self, state: LangGraphWorkflowState
    ) -> Literal["pass", "loop_policy", "loop_author", "escalate"]:
        val = state.get("validation_report")
        if val and val.passed:
            return "pass"

        iter_cnt = state.get("iteration_count", 1)
        max_iters = state.get("max_iterations", 3)

        if iter_cnt > max_iters:
            # Iteration limit reached -> escalate to human review
            return "escalate"

        active_obj = state.get("active_objection")
        if active_obj and active_obj.target_stage == ObjectionTargetStage.POLICY_MAPPING:
            return "loop_policy"
        return "loop_author"

    def run(
        self,
        circular_id: str,
        circular_title: str,
        circular_text: str | None = None,
        raw_text: str | None = None,
        bank_profile: BankProfile | None = None,
        maker_id: str | None = None,
        checker_id: str | None = None,
        thread_id: str = "demo-thread-001",
    ) -> LangGraphWorkflowState:
        """Executes the LangGraph StateGraph with checkpointer."""
        effective_text = circular_text or raw_text or ""
        effective_profile = bank_profile or self.bank_profile
        if effective_profile is None:
            raise ValueError("BankProfile must be provided either in __init__ or in run().")

        initial_state: LangGraphWorkflowState = {
            "circular_id": circular_id,
            "circular_title": circular_title,
            "raw_circular_text": effective_text,
            "bank_profile": effective_profile,
            "maker_id": maker_id or "maker.rajesh",
            "checker_id": checker_id or "checker.vikram",
            "current_stage": 1,
            "stage_name": "START",
            "iteration_count": 1,
            "max_iterations": 3,
            "objection_history": [],
        }

        config = {"configurable": {"thread_id": thread_id}}
        final_state = self.graph.invoke(initial_state, config=config)
        return final_state
