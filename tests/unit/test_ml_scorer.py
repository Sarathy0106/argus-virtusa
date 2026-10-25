from services.cognition.models.scorer import RiskScorer


def test_scorer_low_risk_baseline():
    scorer = RiskScorer()
    features = {
        "amount": 1500.0,
        "velocity_count_1h": 1,
        "velocity_count_24h": 2,
        "structuring_window_count_24h": 0,
        "graph_hop_distance_to_flagged": 999,
        "shared_device_account_count": 0,
        "amount_to_avg_ratio": 0.8,
        "hour_of_day": 14,
    }

    result = scorer.score(features)
    assert result.risk_band == "LOW"
    assert result.recommended_tier == "T0"
    assert result.risk_score < 0.35


def test_scorer_high_risk_structuring_and_mule_hop():
    scorer = RiskScorer()
    features = {
        "amount": 49500.0,
        "velocity_count_1h": 4,
        "velocity_count_24h": 8,
        "structuring_window_count_24h": 4,
        "graph_hop_distance_to_flagged": 1,
        "shared_device_account_count": 3,
        "amount_to_avg_ratio": 8.5,
        "hour_of_day": 3,
    }

    result = scorer.score(features)
    assert result.risk_band == "HIGH"
    assert result.recommended_tier == "T2"
    assert result.risk_score > 0.75

    # Check top attribution factors
    factor_names = [f.feature_name for f in result.top_factors]
    assert "structuring_window_count_24h" in factor_names
    assert "graph_hop_distance_to_flagged" in factor_names
    assert len(result.top_factors) > 0
