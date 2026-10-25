"""
Policy Evaluation Engine for ARGUS.
Supports both direct REST evaluation against OPA server (http://localhost:8181)
and high-performance local deterministic fallback engine mirroring the Rego rules.
"""

from typing import Any

import httpx

from contracts.common import DecisionOutcome, RiskTier
from services.config import get_settings


class PolicyEvaluationResult:
    def __init__(
        self, outcome: DecisionOutcome, tier: RiskTier, evidence_ids: list[str], bundle_version: str
    ):
        self.outcome = outcome
        self.tier = tier
        self.evidence_ids = sorted(evidence_ids)
        self.bundle_version = bundle_version

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "tier": self.tier.value,
            "evidence_ids": self.evidence_ids,
            "bundle_version": self.bundle_version,
        }


class PolicyEngine:
    def __init__(self, opa_url: str | None = None):
        settings = get_settings()
        self.opa_url = opa_url or settings.OPA_URL
        self.bundle_version = "1.0.0"

    def evaluate_local(self, input_data: dict[str, Any]) -> PolicyEvaluationResult:
        """
        Pure deterministic native implementation of the Rego policies in policies/*.rego.
        Ensures 100% reproducibility in unit tests and offline environments.
        """
        evidence: list[str] = []
        amount = float(input_data.get("amount", 0.0))

        # 1. AML: Structuring Window
        structuring_count = int(input_data.get("structuring_window_count_24h", 0))
        if 45000.0 <= amount < 50000.0 and structuring_count >= 3:
            evidence.append("aml_structuring_window")

        # 2. AML: Velocity Burst
        v_1h = int(input_data.get("velocity_count_1h", 0))
        v_24h = int(input_data.get("velocity_count_24h", 0))
        if v_1h >= 5 or v_24h >= 15:
            evidence.append("velocity_burst")

        # 3. AML: Rapid Pass-Through (Mule Ring)
        mule_inflow = float(input_data.get("mule_inflow_amount", 0.0))
        mule_delta = float(input_data.get("mule_outflow_delta_minutes", 999.0))
        if mule_inflow >= 200000.0 and mule_delta <= 15:
            evidence.append("rapid_pass_through")

        # 4. AML: Round Amount Smurfing
        repeat_round = int(input_data.get("repeated_round_count", 0))
        if amount >= 10000.0 and (amount % 10000.0 == 0.0) and repeat_round >= 3:
            evidence.append("round_amount_smurfing")

        # 5. AML: Dormant Account Spike
        days_dormant = int(input_data.get("days_since_last_activity", 0))
        if days_dormant >= 180 and amount >= 50000.0:
            evidence.append("dormant_account_spike")

        # 6. Fraud: Device Hopping
        distinct_devices = int(input_data.get("distinct_devices_24h", 0))
        if distinct_devices > 3:
            evidence.append("device_hopping")

        # 7. Fraud: Off-Hours High Value
        hour_of_day = int(input_data.get("hour_of_day", -1))
        if 1 <= hour_of_day <= 5 and amount > 100000.0:
            evidence.append("off_hours_high_value")

        # 8. Fraud: Geo-Velocity Impossible
        geo_dist = float(input_data.get("geo_distance_km", 0.0))
        geo_time = float(input_data.get("geo_time_delta_minutes", 999.0))
        if geo_dist > 1000.0 and geo_time < 60:
            evidence.append("geo_velocity_impossible")

        # 9. KYC: Sanctions Exact Match
        if input_data.get("sanctions_match") is True:
            evidence.append("sanctions_exact_match")

        # 10. KYC: High-Risk Jurisdiction Corridor
        sanctioned_countries = {"PRK", "IRN", "SYR", "CUB", "RUS"}
        country = str(input_data.get("location_country", "IND")).upper()
        if country in sanctioned_countries:
            evidence.append("high_risk_jurisdiction")

        # 11. KYC: Validity Expired
        kyc_status = str(input_data.get("kyc_status", "VALID")).upper()
        days_kyc = int(input_data.get("days_since_kyc_verification", 0))
        if kyc_status == "EXPIRED" or days_kyc > 365:
            evidence.append("kyc_validity_expired")

        # 12. Privacy: Unauthorized Raw PII Query
        if input_data.get("contains_raw_pii") is True and not input_data.get(
            "has_valid_vault_scope"
        ):
            evidence.append("privacy_unauthorized_pii_query")

        # Decision hierarchy
        evidence_set = set(evidence)
        if "sanctions_exact_match" in evidence_set or "high_risk_jurisdiction" in evidence_set:
            outcome = DecisionOutcome.BLOCK
            tier = RiskTier.T3
        elif (
            "geo_velocity_impossible" in evidence_set
            or "privacy_unauthorized_pii_query" in evidence_set
        ):
            outcome = DecisionOutcome.BLOCK
            tier = RiskTier.T2
        elif "rapid_pass_through" in evidence_set:
            outcome = DecisionOutcome.HOLD
            tier = RiskTier.T2
        elif len(evidence) > 0:
            outcome = DecisionOutcome.HOLD
            tier = RiskTier.T1
        else:
            outcome = DecisionOutcome.ALLOW
            tier = RiskTier.T0

        return PolicyEvaluationResult(
            outcome=outcome, tier=tier, evidence_ids=evidence, bundle_version=self.bundle_version
        )

    def evaluate(
        self, input_data: dict[str, Any], prefer_opa_server: bool = False
    ) -> PolicyEvaluationResult:
        """Evaluates inputs against OPA server if available, falling back to deterministic local engine."""
        if prefer_opa_server:
            try:
                response = httpx.post(
                    f"{self.opa_url}/v1/data/argus/main/decision",
                    json={"input": input_data},
                    timeout=1.0,
                )
                if response.status_code == 200:
                    data = response.json().get("result", {})
                    return PolicyEvaluationResult(
                        outcome=DecisionOutcome(data.get("outcome", "ALLOW")),
                        tier=RiskTier(data.get("tier", "T0")),
                        evidence_ids=data.get("evidence_ids", []),
                        bundle_version=data.get("bundle_version", self.bundle_version),
                    )
            except Exception:
                pass  # Fallback to local evaluation
        return self.evaluate_local(input_data)
