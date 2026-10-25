from contracts.common import DecisionOutcome, RiskTier
from services.policy.engine import PolicyEngine


def test_clean_transaction_allow():
    engine = PolicyEngine()
    clean_input = {
        "amount": 2500.0,
        "velocity_count_1h": 1,
        "velocity_count_24h": 2,
        "location_country": "IND",
        "kyc_status": "VALID",
        "days_since_kyc_verification": 60,
    }
    result = engine.evaluate_local(clean_input)
    assert result.outcome == DecisionOutcome.ALLOW
    assert result.tier == RiskTier.T0
    assert len(result.evidence_ids) == 0


def test_aml_structuring_window_hit():
    engine = PolicyEngine()
    structuring_input = {
        "amount": 49200.0,
        "structuring_window_count_24h": 3,
        "location_country": "IND",
    }
    result = engine.evaluate_local(structuring_input)
    assert result.outcome == DecisionOutcome.HOLD
    assert result.tier == RiskTier.T1
    assert "aml_structuring_window" in result.evidence_ids


def test_sanctions_exact_match_block():
    engine = PolicyEngine()
    sanctions_input = {"amount": 500.0, "sanctions_match": True, "location_country": "IND"}
    result = engine.evaluate_local(sanctions_input)
    assert result.outcome == DecisionOutcome.BLOCK
    assert result.tier == RiskTier.T3
    assert "sanctions_exact_match" in result.evidence_ids


def test_high_risk_jurisdiction_block():
    engine = PolicyEngine()
    hostile_input = {"amount": 1000.0, "location_country": "PRK"}
    result = engine.evaluate_local(hostile_input)
    assert result.outcome == DecisionOutcome.BLOCK
    assert result.tier == RiskTier.T3
    assert "high_risk_jurisdiction" in result.evidence_ids


def test_mule_rapid_pass_through_hold():
    engine = PolicyEngine()
    mule_input = {
        "amount": 150000.0,
        "mule_inflow_amount": 450000.0,
        "mule_outflow_delta_minutes": 8.0,
        "location_country": "IND",
    }
    result = engine.evaluate_local(mule_input)
    assert result.outcome == DecisionOutcome.HOLD
    assert result.tier == RiskTier.T2
    assert "rapid_pass_through" in result.evidence_ids


def test_fraud_device_hopping_hold():
    engine = PolicyEngine()
    hopping_input = {"amount": 5000.0, "distinct_devices_24h": 4, "location_country": "IND"}
    result = engine.evaluate_local(hopping_input)
    assert result.outcome == DecisionOutcome.HOLD
    assert result.tier == RiskTier.T1
    assert "device_hopping" in result.evidence_ids


def test_geo_velocity_impossible_block():
    engine = PolicyEngine()
    impossible_geo_input = {
        "amount": 10000.0,
        "geo_distance_km": 6500.0,
        "geo_time_delta_minutes": 25,
        "location_country": "IND",
    }
    result = engine.evaluate_local(impossible_geo_input)
    assert result.outcome == DecisionOutcome.BLOCK
    assert result.tier == RiskTier.T2
    assert "geo_velocity_impossible" in result.evidence_ids
