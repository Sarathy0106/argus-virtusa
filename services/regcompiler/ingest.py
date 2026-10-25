"""
Regulation Corpus Ingestion and Temporal Indexing for ARGUS.
Parses regulatory circulars into versioned clauses with bitemporal valid-time coordinates.
Provides hybrid keyword (BM25) and semantic retrieval with as-of-date filtering.
"""

import math
import re
from datetime import datetime, timezone

from contracts.memory import RegulationClause


def tokenize_query(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_\-]+\b", text) if len(w) > 2]


class RegulationCorpusIndex:
    def __init__(self):
        # In-memory storage: clause_id -> RegulationClause
        self.clauses: dict[str, RegulationClause] = {}
        # Term frequency index for BM25
        self.inverted_index: dict[str, set[str]] = {}
        self.doc_lengths: dict[str, int] = {}
        self.avg_doc_length: float = 0.0

    def add_clause(self, clause: RegulationClause) -> None:
        self.clauses[clause.id] = clause
        tokens = tokenize_query(clause.clause_text + " " + clause.title)
        self.doc_lengths[clause.id] = len(tokens)

        for token in tokens:
            if token not in self.inverted_index:
                self.inverted_index[token] = set()
            self.inverted_index[token].add(clause.id)

        if self.clauses:
            self.avg_doc_length = sum(self.doc_lengths.values()) / len(self.clauses)

    def search_as_of(
        self, query: str, as_of_date: datetime | None = None, top_k: int = 5
    ) -> list[tuple[RegulationClause, float]]:
        """
        Retrieves top-k clauses using BM25 scoring filtered strictly by as_of_date valid time.
        """
        target_date = as_of_date or datetime.now(timezone.utc)
        query_tokens = tokenize_query(query)
        if not query_tokens:
            return []

        # Find candidate clauses that are business-valid as of target_date
        valid_candidates = {
            cid: c for cid, c in self.clauses.items() if c.valid_from <= target_date <= c.valid_to
        }

        # BM25 Parameters
        k1 = 1.5
        b = 0.75
        n_docs = len(self.clauses)
        scores: dict[str, float] = {}

        for token in query_tokens:
            matching_doc_ids = self.inverted_index.get(token, set()) & valid_candidates.keys()
            df = len(self.inverted_index.get(token, set()))
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)

            for doc_id in matching_doc_ids:
                doc_text = (
                    self.clauses[doc_id].clause_text + " " + self.clauses[doc_id].title
                ).lower()
                tf = doc_text.count(token)
                doc_len = self.doc_lengths.get(doc_id, 1)
                norm_tf = (tf * (k1 + 1)) / (
                    tf + k1 * (1 - b + b * (doc_len / (self.avg_doc_length or 1.0)))
                )
                scores[doc_id] = scores.get(doc_id, 0.0) + (idf * norm_tf)

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return [(self.clauses[doc_id], round(score, 4)) for doc_id, score in ranked[:top_k]]
