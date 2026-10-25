"""
Cost Router and Token Budget Manager for ARGUS.
Implements tiered routing cascade:
Cache -> OPA Rules -> LightGBM ML -> Local LLM (Ollama) -> Fallback.
Enforces per-customer token ceilings with alarms.
"""

from pydantic import BaseModel

from services.cognition.cache.cache import SemanticCache


class BudgetExceededError(Exception):
    """Raised when customer or session has consumed maximum allotted token budget."""

    pass


class RoutingTier(BaseModel):
    tier_name: str  # CACHE, RULES, ML_FILTER, LOCAL_LLM, HOSTED_FALLBACK
    estimated_tokens: int
    cost_usd: float
    reason: str


class CostRouter:
    def __init__(
        self, cache: SemanticCache | None = None, daily_token_budget_per_user: int = 15000
    ):
        self.cache = cache or SemanticCache()
        self.daily_budget = daily_token_budget_per_user
        # User token consumption: user_id -> tokens_consumed
        self.user_usage: dict[str, int] = {}

    def get_user_consumption(self, user_id: str) -> int:
        return self.user_usage.get(user_id, 0)

    def record_token_usage(self, user_id: str, tokens: int) -> None:
        current = self.user_usage.get(user_id, 0)
        new_total = current + tokens
        self.user_usage[user_id] = new_total

    def determine_route(
        self,
        user_id: str,
        query_text: str | None,
        rule_bundle_ver: str,
        requires_complex_narrative: bool = False,
        hard_rule_hit: bool = False,
    ) -> RoutingTier:
        """
        Determines the cheapest sufficient execution tier.
        """
        # 1. Check Semantic Cache if query text provided
        if query_text:
            cached = self.cache.get(query_text, rule_bundle_ver)
            if cached is not None:
                return RoutingTier(
                    tier_name="CACHE",
                    estimated_tokens=0,
                    cost_usd=0.0,
                    reason="Resolved from version-pinned semantic cache (0 latency, 0 tokens)",
                )

        # 2. Hard Policy Rule hit: Bypasses LLM entirely
        if hard_rule_hit:
            return RoutingTier(
                tier_name="RULES",
                estimated_tokens=0,
                cost_usd=0.0,
                reason="Hard policy rule hit (Sanctions/AML). Bypasses generative LLM path.",
            )

        # 3. If routine/no complex narrative required: ML Scorer suffices
        if not requires_complex_narrative:
            return RoutingTier(
                tier_name="ML_FILTER",
                estimated_tokens=0,
                cost_usd=0.0,
                reason="LightGBM score + TreeSHAP attribution provides complete sufficient explanation.",
            )

        # 4. Check token budget for generative tasks
        consumed = self.get_user_consumption(user_id)
        estimated_llm_tokens = 350
        if consumed + estimated_llm_tokens > self.daily_budget:
            # Fall back to structured template rather than failing entirely
            return RoutingTier(
                tier_name="ML_FILTER",
                estimated_tokens=0,
                cost_usd=0.0,
                reason=f"Token budget ceiling reached ({consumed}/{self.daily_budget}). Fallback to deterministic template.",
            )

        # 5. Route to local LLM (Ollama)
        self.record_token_usage(user_id, estimated_llm_tokens)
        return RoutingTier(
            tier_name="LOCAL_LLM",
            estimated_tokens=estimated_llm_tokens,
            cost_usd=0.0,  # Zero per-token API cost on local hardware
            reason="Routed to local Ollama (Qwen2.5/Llama3.1) for evidence-bound narrative drafting.",
        )
