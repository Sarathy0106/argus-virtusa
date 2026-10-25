"""
Analyst Feedback Loop for ARGUS Memory.
Learns from analyst verdicts (CONFIRMED_FRAUD, FALSE_POSITIVE)
to update procedural memory, tune rule weights, and store episodic history.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class AnalystFeedback(BaseModel):
    case_id: str
    decision_id: str
    analyst_id: str
    verdict: str  # CONFIRMED_SUSPICIOUS, FALSE_POSITIVE, MITIGATED
    notes: str
    rules_applied: list[str]
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeedbackLoopManager:
    def __init__(self):
        self.feedback_history: list[AnalystFeedback] = []
        # Rule reliability weights: rule_name -> float (1.0 default)
        self.rule_weights: dict[str, float] = {}

    def submit_feedback(
        self,
        case_id: str,
        decision_id: str,
        analyst_id: str,
        verdict: str,
        notes: str,
        rules_applied: list[str],
    ) -> AnalystFeedback:
        fb = AnalystFeedback(
            case_id=case_id,
            decision_id=decision_id,
            analyst_id=analyst_id,
            verdict=verdict,
            notes=notes,
            rules_applied=rules_applied,
        )
        self.feedback_history.append(fb)

        # Update procedural weights
        for rule in rules_applied:
            current_weight = self.rule_weights.get(rule, 1.0)
            if verdict == "FALSE_POSITIVE":
                # Down-weight noisy rule slightly
                self.rule_weights[rule] = max(0.2, round(current_weight * 0.95, 3))
            elif verdict == "CONFIRMED_SUSPICIOUS":
                # Strengthen verified rule
                self.rule_weights[rule] = min(2.0, round(current_weight * 1.05, 3))

        return fb

    def get_rule_weight(self, rule_name: str) -> float:
        return self.rule_weights.get(rule_name, 1.0)

    def get_feedback_for_case(self, case_id: str) -> list[AnalystFeedback]:
        return [fb for fb in self.feedback_history if fb.case_id == case_id]
