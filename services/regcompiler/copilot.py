"""
Evidence-Grounded Regulatory Compliance Copilot for ARGUS.
Answers compliance queries strictly citing in-force regulation clauses.
Enforces explicit abstention when evidence is insufficient or confidence is low.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from services.cognition.verifier.verifier import EvidenceVerifier
from services.regcompiler.ingest import RegulationCorpusIndex


class CopilotAnswer(BaseModel):
    query: str
    as_of_date: str
    answer: str
    cited_clauses: list[str]
    abstained: bool
    confidence: float
    sources: list[dict[str, Any]] = Field(default_factory=list)


class ComplianceCopilot:
    def __init__(
        self, corpus: RegulationCorpusIndex | None = None, verifier: EvidenceVerifier | None = None
    ):
        self.corpus = corpus or RegulationCorpusIndex()
        self.verifier = verifier or EvidenceVerifier()

    def answer_query(self, query: str, as_of_date: datetime | None = None) -> CopilotAnswer:
        target_date = as_of_date or datetime.now(UTC)
        results = self.corpus.search_as_of(query, as_of_date=target_date, top_k=3)

        # 1. Abstention Gate: If no relevant clauses match
        if not results or results[0][1] < 0.5:
            return CopilotAnswer(
                query=query,
                as_of_date=target_date.isoformat(),
                answer="ABSTAIN: I cannot provide a verified answer based on the regulations in-force as of the requested date.",
                cited_clauses=[],
                abstained=True,
                confidence=0.0,
                sources=[],
            )

        top_clause, score = results[0]
        valid_clause_ids = [c.clause_ref for c, _ in results]

        # 2. Evidence-bound answer drafting
        candidate_answer = (
            f"Under {top_clause.title} ({top_clause.clause_ref}) [CLAUSE:{top_clause.clause_ref}]:\n"
            f"{top_clause.clause_text}\n"
            f"(Verified in-force as of {target_date.strftime('%Y-%m-%d')})"
        )

        fallback = (
            f"Refer to official in-force directive: {top_clause.clause_ref} "
            f"({top_clause.title}) effective {top_clause.valid_from.strftime('%Y-%m-%d')}."
        )

        # 3. Evidence Verifier Gate
        verification = self.verifier.verify_and_gate(
            candidate_text=candidate_answer,
            valid_evidence_ids=valid_clause_ids,
            fallback_template=fallback,
        )

        sources_payload = [
            {
                "clause_ref": c.clause_ref,
                "title": c.title,
                "score": s,
                "valid_from": c.valid_from.isoformat(),
                "valid_to": c.valid_to.isoformat(),
            }
            for c, s in results
        ]

        return CopilotAnswer(
            query=query,
            as_of_date=target_date.isoformat(),
            answer=verification.approved_text,
            cited_clauses=verification.cited_ids,
            abstained=False,
            confidence=min(1.0, score / 3.0),
            sources=sources_payload,
        )
