"""
Reg-to-Rule Compiler and Historical Impact Simulator for ARGUS.
Compiles regulatory circular obligations into executable Rego policies,
simulates impact on historical transaction data, and gates deployment via Maker-Checker signoff.
"""

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from contracts.obligations import RegulatoryObligation
from contracts.transactions import Transaction
from services.ledger.ledger import AuditLedger
from services.policy.engine import PolicyEngine


class ImpactSimulationReport(BaseModel):
    rule_ref: str
    total_txns_analyzed: int
    baseline_alert_count: int
    new_alert_count: int
    alert_increase_count: int
    delta_percentage: float
    total_flagged_volume_inr: float
    sample_triggered_ids: list[str]


class CompilationResult(BaseModel):
    obligation: RegulatoryObligation
    draft_rego_code: str
    draft_test_code: str
    simulation_report: ImpactSimulationReport | None = None
    published: bool = False
    bundle_version: str | None = None


class RegToRuleCompiler:
    def __init__(
        self, policy_engine: PolicyEngine | None = None, audit_ledger: AuditLedger | None = None
    ):
        self.policy_engine = policy_engine or PolicyEngine()
        self.audit_ledger = audit_ledger or AuditLedger()

    def compile_obligation_to_rego(self, obligation: RegulatoryObligation) -> tuple[str, str]:
        """Synthesizes draft Rego policy code and unit tests from obligation conditions."""
        rule_name = obligation.rule_ref.lower().replace("-", "_")
        threshold = obligation.condition_json.get("threshold_amount", 50000.0)
        channel = obligation.condition_json.get("channel", "UPI")

        # Draft Rego Rule
        rego_code = (
            f"package argus.compiled.{rule_name}\n\n"
            f"# Auto-compiled from Obligation: {obligation.id} (Clause: {obligation.clause_id})\n"
            f'version := "1.0.0"\n\n'
            f"rule_hit if {{\n"
            f"    input.amount >= {threshold}\n"
            f'    input.channel == "{channel}"\n'
            f"}}\n\n"
            f"decision := {{\n"
            f'    "outcome": "{obligation.action_json.get("action", "HOLD")}",\n'
            f'    "tier": "{obligation.action_json.get("tier", "T1")}",\n'
            f'    "evidence_id": "{obligation.rule_ref}"\n'
            f"}}\n"
        )

        # Draft Unit Test
        test_code = (
            f"package argus.compiled.{rule_name}_test\n\n"
            f"import data.argus.compiled.{rule_name}\n\n"
            f"test_threshold_hit if {{\n"
            f'    rule_hit with input as {{"amount": {threshold + 1000}, "channel": "{channel}"}}\n'
            f"}}\n\n"
            f"test_threshold_miss if {{\n"
            f'    not rule_hit with input as {{"amount": {threshold - 1000}, "channel": "{channel}"}}\n'
            f"}}\n"
        )
        return rego_code, test_code

    def simulate_historical_impact(
        self, obligation: RegulatoryObligation, historical_txns: list[Transaction]
    ) -> ImpactSimulationReport:
        """
        Simulates how many additional transactions would have been flagged
        if this candidate rule was active on historical data.
        """
        threshold = obligation.condition_json.get("threshold_amount", 50000.0)
        target_channel = obligation.condition_json.get("channel", "UPI")

        baseline_hits = 0
        new_rule_hits = 0
        triggered_ids = []
        flagged_volume = 0.0

        for txn in historical_txns:
            # Baseline evaluation
            input_data = {
                "amount": txn.amount,
                "location_country": txn.location_country,
                "channel": txn.channel.value,
            }
            res = self.policy_engine.evaluate_local(input_data)
            if res.outcome.value in ("HOLD", "BLOCK"):
                baseline_hits += 1

            # Candidate rule evaluation
            candidate_hit = txn.amount >= threshold and txn.channel.value == target_channel
            if candidate_hit:
                new_rule_hits += 1
                triggered_ids.append(txn.id)
                flagged_volume += txn.amount

        total = len(historical_txns)
        delta_pct = round((new_rule_hits / (total or 1)) * 100, 2)

        return ImpactSimulationReport(
            rule_ref=obligation.rule_ref,
            total_txns_analyzed=total,
            baseline_alert_count=baseline_hits,
            new_alert_count=new_rule_hits,
            alert_increase_count=new_rule_hits,
            delta_percentage=delta_pct,
            total_flagged_volume_inr=round(flagged_volume, 2),
            sample_triggered_ids=triggered_ids[:10],
        )

    def publish_rule_bundle(
        self,
        compilation: CompilationResult,
        maker_id: str,
        checker_id: str,
        target_policy_dir: Path | None = None,
    ) -> CompilationResult:
        """
        Maker-Checker gated publishing of the new rule bundle.
        Writes to policy directory and logs signed audit ledger entry.
        """
        if not maker_id or not checker_id or maker_id == checker_id:
            raise PermissionError(
                "Rule publication requires dual independent Maker-Checker signoffs."
            )

        out_dir = target_policy_dir or Path("policies") / "compiled"
        out_dir.mkdir(parents=True, exist_ok=True)

        rule_file = out_dir / f"{compilation.obligation.rule_ref.lower()}.rego"
        rule_file.write_text(compilation.draft_rego_code, encoding="utf-8")

        new_version = "1.1.0"
        compilation.published = True
        compilation.bundle_version = new_version

        # Commit to Audit Ledger
        self.audit_ledger.append(
            event_type="RULE_BUNDLE_PUBLISHED",
            entity_id=compilation.obligation.rule_ref,
            signer=f"maker:{maker_id}|checker:{checker_id}",
            payload={
                "obligation_id": compilation.obligation.id,
                "rule_ref": compilation.obligation.rule_ref,
                "new_bundle_version": new_version,
                "impact_simulation": compilation.simulation_report.model_dump()
                if compilation.simulation_report
                else None,
                "published_at": datetime.now(UTC).isoformat(),
            },
        )
        return compilation
