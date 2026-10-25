"""
Transaction Risk Agent for ARGUS Mesh.
Skill: risk.score_transaction
Evaluates hard OPA rules and calibrated ML risk scores with feature attribution.
"""

from typing import Any

from contracts.agents import AgentCard, AgentSkill
from contracts.transactions import Transaction
from services.agents.crypto import AgentKeyPair
from services.cognition.features.pipeline import FeaturePipeline
from services.cognition.models.scorer import RiskScorer
from services.policy.engine import PolicyEngine


class TxnRiskAgent:
    def __init__(
        self,
        keypair: AgentKeyPair | None = None,
        feature_pipeline: FeaturePipeline | None = None,
        policy_engine: PolicyEngine | None = None,
        risk_scorer: RiskScorer | None = None,
    ):
        self.keypair = keypair or AgentKeyPair()
        self.feature_pipeline = feature_pipeline or FeaturePipeline()
        self.policy_engine = policy_engine or PolicyEngine()
        self.risk_scorer = risk_scorer or RiskScorer()

        self.card = AgentCard(
            agent_id="agent.txn_risk",
            name="Transaction Risk Evaluation Agent",
            version="1.0.0",
            public_key=self.keypair.public_key_hex,
            skills=[
                AgentSkill(
                    name="risk.score_transaction",
                    description="Calculates deterministic OPA policy verdict, calibrated ML score, and SHAP factors",
                )
            ],
        )

    def evaluate_transaction(self, transaction: Transaction) -> dict[str, Any]:
        """Executes the dual-engine evaluation: Policy Engine + ML Risk Scorer."""
        # 1. Ingest into pipeline and extract features
        self.feature_pipeline.ingest_transaction(transaction)
        features = self.feature_pipeline.extract_features(transaction)

        # 2. Hard Policy Engine (OPA)
        policy_res = self.policy_engine.evaluate_local(features)

        # 3. Calibrated ML Scorer
        ml_res = self.risk_scorer.score(features)

        # Combine: Policy engine is authoritative for hard blocks/holds.
        # If policy allows, ML score determines if it needs T1 analyst review.
        if policy_res.outcome.value in ("BLOCK", "HOLD"):
            final_outcome = policy_res.outcome.value
            final_tier = policy_res.tier.value
        elif ml_res.recommended_tier in ("T1", "T2"):
            final_outcome = "HOLD"
            final_tier = ml_res.recommended_tier
        else:
            final_outcome = "ALLOW"
            final_tier = "T0"

        evidence = sorted(
            list(set(policy_res.evidence_ids + [f.feature_name for f in ml_res.top_factors]))
        )

        return {
            "transaction_id": transaction.id,
            "outcome": final_outcome,
            "tier": final_tier,
            "risk_score": ml_res.risk_score,
            "risk_band": ml_res.risk_band,
            "evidence_ids": evidence,
            "top_factors": [f.model_dump() for f in ml_res.top_factors],
            "rule_bundle_ver": policy_res.bundle_version,
            "model_ver": ml_res.model_version,
        }
