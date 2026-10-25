"""
Deterministic Decision Replay Engine for ARGUS.
Re-executes archived decision inputs against pinned rule bundles and model versions.
Verifies bit-for-bit output hash identity.
"""

from typing import Any

from pydantic import BaseModel, Field

from contracts.decisions import DecisionRecord
from services.policy.engine import PolicyEngine


class ReplayReport(BaseModel):
    decision_id: str
    replayed_success: bool
    input_hash_match: bool
    output_hash_match: bool
    original_outcome: str
    replayed_outcome: str
    original_tier: str
    replayed_tier: str
    original_evidence_ids: list[str]
    replayed_evidence_ids: list[str]
    delta: dict[str, Any] = Field(default_factory=dict)


class ReplayEngine:
    def __init__(self, policy_engine: PolicyEngine | None = None):
        self.policy_engine = policy_engine or PolicyEngine()

    def replay_decision(
        self, archived_record: DecisionRecord, original_input_data: dict[str, Any]
    ) -> ReplayReport:
        """
        Re-executes original input data against policy engine.
        Compares recomputed hashes and verdicts against archived decision.
        """
        eval_result = self.policy_engine.evaluate_local(original_input_data)

        # Re-construct decision record using identical canonical hashing
        replayed_record = DecisionRecord.create(
            decision_id=archived_record.id,
            transaction_id=archived_record.transaction_id,
            input_data=original_input_data,
            rule_bundle_ver=archived_record.rule_bundle_ver,
            model_ver=archived_record.model_ver,
            risk_score=archived_record.risk_score,
            outcome=eval_result.outcome,
            tier=eval_result.tier,
            evidence_ids=eval_result.evidence_ids,
            explanation_summary=archived_record.explanation_summary,
            recorded_at=archived_record.recorded_at,
        )

        input_match = archived_record.input_hash == replayed_record.input_hash
        output_match = archived_record.output_hash == replayed_record.output_hash

        delta = {}
        if not input_match:
            delta["input_hash"] = {
                "archived": archived_record.input_hash,
                "replayed": replayed_record.input_hash,
            }
        if not output_match:
            delta["output_hash"] = {
                "archived": archived_record.output_hash,
                "replayed": replayed_record.output_hash,
            }
        if archived_record.outcome != eval_result.outcome:
            delta["outcome"] = {
                "archived": archived_record.outcome.value,
                "replayed": eval_result.outcome.value,
            }

        success = input_match and output_match

        return ReplayReport(
            decision_id=archived_record.id,
            replayed_success=success,
            input_hash_match=input_match,
            output_hash_match=output_match,
            original_outcome=archived_record.outcome.value,
            replayed_outcome=eval_result.outcome.value,
            original_tier=archived_record.tier.value,
            replayed_tier=eval_result.tier.value,
            original_evidence_ids=archived_record.evidence_ids,
            replayed_evidence_ids=eval_result.evidence_ids,
            delta=delta,
        )
