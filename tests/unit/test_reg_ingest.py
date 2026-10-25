from datetime import datetime, timezone

from contracts.memory import RegulationClause
from services.regcompiler.ingest import RegulationCorpusIndex


def test_regulation_corpus_bm25_and_temporal_filtering():
    corpus = RegulationCorpusIndex()

    # Clause 1: Effective 2024 onwards
    c1 = RegulationClause(
        id="RBI-KYC-C23",
        doc_id="RBI-MD-KYC-2016",
        title="Periodic Updation of KYC",
        clause_ref="Clause-23",
        clause_text="Regulated entities shall conduct periodic review and KYC updation every 2 years for high risk customers.",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
    )

    # Clause 2: Effective 2026 onwards (V-CIP video KYC amendment)
    c2 = RegulationClause(
        id="RBI-KYC-C54",
        doc_id="RBI-AMEND-2026",
        title="Video-based Customer Identification Process (V-CIP)",
        clause_ref="Clause-54",
        clause_text="Video-based Customer Identification Process is recognized as equivalent to physical face-to-face verification.",
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
    )

    corpus.add_clause(c1)
    corpus.add_clause(c2)

    # Search in year 2024: Should find Clause-23, but NOT Clause-54 (not valid yet!)
    res_2024 = corpus.search_as_of(
        "periodic review high risk", as_of_date=datetime(2024, 6, 1, tzinfo=timezone.utc)
    )
    assert len(res_2024) > 0
    assert res_2024[0][0].clause_ref == "Clause-23"

    # Search for V-CIP in 2024: Must return empty (not in-force yet!)
    res_vcip_2024 = corpus.search_as_of(
        "video verification V-CIP", as_of_date=datetime(2024, 6, 1, tzinfo=timezone.utc)
    )
    assert len(res_vcip_2024) == 0

    # Search for V-CIP in 2026: Should find Clause-54!
    res_vcip_2026 = corpus.search_as_of(
        "video verification V-CIP", as_of_date=datetime(2026, 3, 1, tzinfo=timezone.utc)
    )
    assert len(res_vcip_2026) > 0
    assert res_vcip_2026[0][0].clause_ref == "Clause-54"
