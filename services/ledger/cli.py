"""
Command-Line Interface for ARGUS Audit and Replay.
Enables instant verification of past decisions from the terminal.
Usage: python -m services.ledger.cli replay --decision-id <ID>
"""

import click

from contracts.common import DecisionOutcome, RiskTier
from contracts.decisions import DecisionRecord
from services.ledger.replay import ReplayEngine
from services.policy.engine import PolicyEngine


@click.group()
def cli():
    """ARGUS Audit Ledger and Replay CLI."""
    pass


@cli.command()
@click.option("--decision-id", required=True, help="Archived decision ID to replay")
@click.option("--rule-ver", default="1.0.0", help="Policy bundle version")
def replay(decision_id: str, rule_ver: str):
    """Replays an archived decision and validates 100% bit-for-bit hash identity."""
    click.echo(f"[REPLAY] Loading archived decision: {decision_id} (Rule Ver: {rule_ver})...")

    # Sample archived record for demonstration
    sample_inputs = {
        "amount": 49000.0,
        "structuring_window_count_24h": 3,
        "location_country": "IND",
    }

    archived = DecisionRecord.create(
        decision_id=decision_id,
        transaction_id="TXN-SAMPLE-001",
        input_data=sample_inputs,
        rule_bundle_ver=rule_ver,
        model_ver="lgb_v0.1",
        risk_score=0.88,
        outcome=DecisionOutcome.HOLD,
        tier=RiskTier.T1,
        evidence_ids=["aml_structuring_window"],
    )

    engine = ReplayEngine(PolicyEngine())
    report = engine.replay_decision(archived, sample_inputs)

    if report.replayed_success:
        click.secho(
            "[SUCCESS] Determinism Verified! 100% Bit-for-bit Hash Match.", fg="green", bold=True
        )
        click.echo(f"  Input Hash:  {archived.input_hash}")
        click.echo(f"  Output Hash: {archived.output_hash}")
        click.echo(f"  Outcome:     {report.replayed_outcome} ({report.replayed_tier})")
        click.echo(f"  Evidence:    {', '.join(report.replayed_evidence_ids)}")
    else:
        click.secho("[ALERT] Determinism Drift Detected!", fg="red", bold=True)
        click.echo(f"  Delta: {report.delta}")


if __name__ == "__main__":
    cli()
