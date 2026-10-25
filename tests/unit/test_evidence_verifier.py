from services.cognition.verifier.verifier import EvidenceVerifier


def test_evidence_verifier_approves_valid_citations():
    verifier = EvidenceVerifier()
    text = (
        "The transfer exhibits classic structuring traits [EVID:aml_structuring_window] "
        "and abnormal off-hours timing [EVID:off_hours_high_value]."
    )
    valid_ids = ["aml_structuring_window", "off_hours_high_value", "some_other_id"]
    fallback = "FALLBACK TEMPLATE"

    res = verifier.verify_and_gate(text, valid_ids, fallback)
    assert res.is_valid is True
    assert res.approved_text == text
    assert set(res.cited_ids) == {"aml_structuring_window", "off_hours_high_value"}
    assert len(res.hallucinated_ids) == 0


def test_evidence_verifier_rejects_hallucinated_citations():
    verifier = EvidenceVerifier()
    # Mentions a made-up evidence ID "fake_rule_never_triggered"
    hallucinated_text = (
        "Account flagged under structuring [EVID:aml_structuring_window] "
        "and fake rule [EVID:fake_rule_never_triggered]."
    )
    valid_ids = ["aml_structuring_window"]
    fallback = "DETERMINISTIC FALLBACK TEMPLATE"

    res = verifier.verify_and_gate(hallucinated_text, valid_ids, fallback)
    assert res.is_valid is False
    assert res.approved_text == fallback
    assert "fake_rule_never_triggered" in res.hallucinated_ids
    assert "Hallucinated citations detected" in (res.rejection_reason or "")


def test_evidence_verifier_rejects_missing_citations():
    verifier = EvidenceVerifier()
    uncited_text = "This customer definitely committed fraud and should be arrested immediately."
    valid_ids = ["aml_structuring_window"]
    fallback = "DETERMINISTIC FALLBACK TEMPLATE"

    res = verifier.verify_and_gate(uncited_text, valid_ids, fallback)
    assert res.is_valid is False
    assert res.approved_text == fallback
    assert "No verifiable citations found" in (res.rejection_reason or "")
