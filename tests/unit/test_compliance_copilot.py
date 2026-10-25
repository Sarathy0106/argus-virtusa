from datetime import datetime, timezone

from contracts.memory import RegulationClause
from services.regcompiler.copilot import ComplianceCopilot
from services.regcompiler.ingest import RegulationCorpusIndex


def test_compliance_copilot_grounded_answer():
    corpus = RegulationCorpusIndex()
    c = RegulationClause(
        id="RBI-WIRE-01",
        doc_id="RBI-DIR-2024",
        title="Cross-Border Outward Wire Transfers",
        clause_ref="Clause-12A",
        clause_text="All outward remittances exceeding USD 10,000 or INR 800,000 must include verified beneficiary identifiers.",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
    )
    corpus.add_clause(c)

    copilot = ComplianceCopilot(corpus=corpus)
    ans = copilot.answer_query(
        "What is the reporting threshold for outward remittances wire transfers?"
    )

    assert ans.abstained is False
    assert "Clause-12A" in ans.cited_clauses
    assert "[CLAUSE:Clause-12A]" in ans.answer
    assert ans.confidence > 0.0


def test_compliance_copilot_abstention_on_unrelated_query():
    corpus = RegulationCorpusIndex()
    copilot = ComplianceCopilot(corpus=corpus)

    # Asking a question with no applicable regulation in the index
    ans = copilot.answer_query("Can banks accept payment in Martian space currency?")
    assert ans.abstained is True
    assert "ABSTAIN" in ans.answer
    assert len(ans.cited_clauses) == 0
