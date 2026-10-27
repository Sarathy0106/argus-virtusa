"""
Backtest Agent for ARGUS v2 (Stage 5).
Replays historical transaction datasets through baseline rules versus
the draft candidate rule within an isolated sandbox environment.
"""

import time

from pydantic import BaseModel, Field

from contracts.agents import AgentCard, AgentSkill
from contracts.rule_dsl import RuleDefinition
from contracts.transactions import Transaction
from services.agents.crypto import AgentKeyPair
from services.policy.engine import PolicyEngine
from services.regcompiler.dsl_compiler import RuleDSLCompiler


class SegmentCount(BaseModel):
    segment: str
    baseline_alerts: int
    candidate_alerts: int
    delta_alerts: int


class BacktestResult(BaseModel):
    rule_name: str
    rule_version: str
    total_txns: int
    baseline_alerts: int
    candidate_alerts: int
    delta_alerts: int
    delta_percentage: float
    total_flagged_volume: float
    flagged_txn_ids: list[str] = Field(default_factory=list)
    avg_latency_ms: float = 0.0
    sandbox_status: str = "COMPLETED"
    segments: list[SegmentCount] = Field(default_factory=list)
    ops_hours_per_day: float = 0.0
    data_source: str = "synthetic_in_memory"


class BacktestAgent:
    def __init__(
        self,
        key_pair: AgentKeyPair | None = None,
        policy_engine: PolicyEngine | None = None,
        compiler: RuleDSLCompiler | None = None,
    ):
        self.key_pair = key_pair or AgentKeyPair()
        self.policy_engine = policy_engine or PolicyEngine()
        self.compiler = compiler or RuleDSLCompiler()
        self.agent_id = "agent.backtest"
        self.card = AgentCard(
            agent_id=self.agent_id,
            name="Backtest Sandbox Agent",
            version="2.0.0",
            public_key=self.key_pair.public_key_hex,
            skills=[
                AgentSkill(
                    name="backtest.replay_historical",
                    description="Simulates draft vs baseline rule impact on historical transaction data.",
                )
            ],
        )

    def run_duckdb_backtest(
        self,
        rule_def: RuleDefinition,
        baseline: RuleDefinition | None = None,
        progress_cb=None,
    ) -> BacktestResult:
        """Real backtest over the 500k parquet via DuckDB (B5). All counts come
        from SQL aggregation over actual rows."""
        from services.backtest.duck import DuckBacktestEngine

        engine = DuckBacktestEngine()
        r = engine.run(rule_def, baseline=baseline, progress_cb=progress_cb)
        return BacktestResult(
            rule_name=r.rule_name,
            rule_version=r.rule_version,
            total_txns=r.total_rows,
            baseline_alerts=r.baseline_alerts,
            candidate_alerts=r.candidate_alerts,
            delta_alerts=r.delta_alerts,
            delta_percentage=r.delta_percentage,
            total_flagged_volume=r.candidate_flagged_volume_inr,
            ops_hours_per_day=r.ops_hours_per_day,
            segments=[
                SegmentCount(
                    segment=s.segment,
                    baseline_alerts=s.baseline_alerts,
                    candidate_alerts=s.candidate_alerts,
                    delta_alerts=s.delta_alerts,
                )
                for s in r.segments
            ],
            data_source="duckdb_500k_parquet",
        )

    def run_backtest(
        self, rule_def: RuleDefinition, transactions: list[Transaction] | None = None
    ) -> BacktestResult:
        """
        Executes Stage 5 Backtesting:
        Replays transactions across baseline policy engine vs candidate RuleDefinition.
        """
        t0 = time.perf_counter()
        if transactions is None:
            from services.ingest.simulator import SyntheticTransactionGenerator
            gen = SyntheticTransactionGenerator(seed=42)
            transactions = gen.generate_dataset(100)
        total = len(transactions)
        baseline_hits = 0
        candidate_hits = 0
        flagged_ids = []
        flagged_volume = 0.0

        for txn in transactions:
            # Baseline policy engine evaluation
            eval_input = {
                "amount": txn.amount,
                "channel": txn.channel.value,
                "location_country": txn.location_country,
                "counterparty_token": txn.counterparty_token,
            }
            base_res = self.policy_engine.evaluate_local(eval_input)
            if base_res.outcome.value in ("HOLD", "BLOCK"):
                baseline_hits += 1

            # Candidate rule evaluation in sandbox
            cand_res = self.compiler.evaluate_locally(rule_def, eval_input)
            if cand_res.get("rule_hit"):
                candidate_hits += 1
                flagged_ids.append(txn.id)
                flagged_volume += txn.amount

        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_latency = round(elapsed_ms / (total or 1), 3)

        delta_count = candidate_hits - baseline_hits
        delta_pct = round((candidate_hits / (total or 1)) * 100, 2)

        return BacktestResult(
            rule_name=rule_def.rule_name,
            rule_version=rule_def.version,
            total_txns=total,
            baseline_alerts=baseline_hits,
            candidate_alerts=candidate_hits,
            delta_alerts=delta_count,
            delta_percentage=delta_pct,
            total_flagged_volume=round(flagged_volume, 2),
            flagged_txn_ids=flagged_ids[:20],
            avg_latency_ms=avg_latency,
        )
