"""
Semantic Cache for ARGUS Cognition.
Keyed by (tokenized_query_hash, rule_bundle_version) to prevent stale answers
across policy updates. Tracks saved tokens and hit ratios.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    query_hash: str
    rule_bundle_ver: str
    response: dict[str, Any]
    tokens_saved: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SemanticCache:
    def __init__(self):
        self._cache: dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0
        self.total_tokens_saved = 0

    def _generate_key(self, tokenized_query: str, rule_bundle_ver: str) -> str:
        content = f"{tokenized_query.strip().lower()}|{rule_bundle_ver}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get(self, tokenized_query: str, rule_bundle_ver: str) -> dict[str, Any] | None:
        key = self._generate_key(tokenized_query, rule_bundle_ver)
        entry = self._cache.get(key)
        if entry:
            self.hits += 1
            self.total_tokens_saved += entry.tokens_saved
            return entry.response

        self.misses += 1
        return None

    def put(
        self,
        tokenized_query: str,
        rule_bundle_ver: str,
        response: dict[str, Any],
        tokens_saved: int = 250,
    ) -> None:
        key = self._generate_key(tokenized_query, rule_bundle_ver)
        self._cache[key] = CacheEntry(
            query_hash=key,
            rule_bundle_ver=rule_bundle_ver,
            response=response,
            tokens_saved=tokens_saved,
        )

    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return round(self.hits / total, 3)

    def clear(self) -> None:
        self._cache.clear()
        self.hits = 0
        self.misses = 0
        self.total_tokens_saved = 0
