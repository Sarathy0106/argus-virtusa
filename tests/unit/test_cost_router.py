from services.cognition.cache.cache import SemanticCache
from services.cognition.router.router import CostRouter


def test_semantic_cache_version_pinning():
    cache = SemanticCache()
    query = "Is KYC refresh required for dormant account <ACCT_1234>?"

    # Cache answer under Rule Bundle v1.0.0
    cache.put(query, "1.0.0", {"answer": "Yes, periodic review required under Clause 23."})

    # Retrieve under same version -> Hit
    hit = cache.get(query, "1.0.0")
    assert hit is not None
    assert "Clause 23" in hit["answer"]
    assert cache.hits == 1

    # Retrieve under upgraded version v1.1.0 -> Miss! (Prevents outdated regulatory advice)
    miss = cache.get(query, "1.1.0")
    assert miss is None
    assert cache.misses == 1


def test_cost_router_cascades_and_budget_fallback():
    cache = SemanticCache()
    router = CostRouter(cache=cache, daily_token_budget_per_user=1000)

    # 1. Hard rule hit routes to RULES (0 tokens)
    r1 = router.determine_route("user_01", None, "1.0.0", hard_rule_hit=True)
    assert r1.tier_name == "RULES"
    assert r1.estimated_tokens == 0

    # 2. Routine query without narrative need routes to ML_FILTER (0 tokens)
    r2 = router.determine_route("user_01", None, "1.0.0", requires_complex_narrative=False)
    assert r2.tier_name == "ML_FILTER"
    assert r2.estimated_tokens == 0

    # 3. Complex narrative routes to LOCAL_LLM (350 tokens)
    r3 = router.determine_route("user_01", None, "1.0.0", requires_complex_narrative=True)
    assert r3.tier_name == "LOCAL_LLM"
    assert r3.estimated_tokens == 350
    assert router.get_user_consumption("user_01") == 350

    # 4. Another complex narrative routes to LOCAL_LLM
    r4 = router.determine_route("user_01", None, "1.0.0", requires_complex_narrative=True)
    assert r4.tier_name == "LOCAL_LLM"
    assert router.get_user_consumption("user_01") == 700

    # 5. Third complex narrative hits budget ceiling (700 + 350 > 1000) -> Falls back to ML_FILTER
    r5 = router.determine_route("user_01", None, "1.0.0", requires_complex_narrative=True)
    assert r5.tier_name == "ML_FILTER"
    assert "budget" in r5.reason.lower()
