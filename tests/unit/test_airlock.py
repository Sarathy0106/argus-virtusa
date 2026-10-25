import pytest

from services.airlock.airlock import PIIAirlock
from services.airlock.egress import EgressGate, PIILeakageException
from services.airlock.recognizers import IndianPIIRecognizer
from services.airlock.vault import PIIVault


def test_indian_pii_recognizer():
    recognizer = IndianPIIRecognizer()
    text = (
        "Customer Rajesh Kumar with PAN ABCDE1234F and Aadhaar 2345 6789 0123 "
        "transferred funds via UPI rajesh@okhdfcbank to IFSC HDFC0001234. "
        "Contact: +91 9876543210 or rajesh@example.com."
    )

    entities = recognizer.analyze(text)
    types = {e.entity_type for e in entities}

    assert "PAN" in types
    assert "AADHAAR" in types
    assert "UPI" in types
    assert "IFSC" in types
    assert "PHONE" in types
    assert "EMAIL" in types


def test_pii_vault_encryption_roundtrip():
    vault = PIIVault()
    token = vault.tokenize_and_store("PAN", "ABCDE1234F", scope="session_01")
    assert token.startswith("<PAN_")
    assert token.endswith(">")
    assert vault.has_token(token)

    # Authorized role can detokenize
    raw = vault.detokenize(token, requesting_role="compliance_officer", scope="session_01")
    assert raw == "ABCDE1234F"

    # Unauthorized role is blocked
    with pytest.raises(PermissionError):
        vault.detokenize(token, requesting_role="unauthorized_guest", scope="session_01")


def test_airlock_tokenization_and_detokenization():
    airlock = PIIAirlock()
    original_text = "Please check customer with PAN FGHIJ5678K and phone 9876543210."
    tokenized = airlock.tokenize_text(original_text, scope="case_101")

    # Raw PII must be replaced with typed tokens
    assert "FGHIJ5678K" not in tokenized
    assert "9876543210" not in tokenized
    assert "<PAN_" in tokenized
    assert "<PHONE_" in tokenized

    # Detokenize with authorized role
    restored = airlock.detokenize_text(
        tokenized, requesting_role="authorized_analyst", scope="case_101"
    )
    assert "FGHIJ5678K" in restored
    assert "9876543210" in restored


def test_egress_gate_blocks_raw_pii():
    gate = EgressGate()

    # Safe tokenized payload passes
    safe_text = "Transaction from <ACCT_7F3A> flagged under policy aml_structuring_window."
    assert gate.is_safe(safe_text) is True

    # Leaked PAN is blocked
    leaked_pan_text = "Customer PAN is ABCDE1234F."
    with pytest.raises(PIILeakageException) as exc_info:
        gate.inspect_and_enforce(leaked_pan_text)
    assert exc_info.value.detected_kind == "PAN"

    # Leaked Aadhaar is blocked
    leaked_aadhaar = "Aadhaar verified as 3456 7890 1234."
    with pytest.raises(PIILeakageException) as exc_info:
        gate.inspect_and_enforce(leaked_aadhaar)
    assert exc_info.value.detected_kind == "AADHAAR"


def test_zero_leakage_across_corpus():
    """Validates that tokenizing arbitrary messy text leaves zero detectable raw PII."""
    airlock = PIIAirlock()
    messy_inputs = [
        "Aadhaar: 4321 8765 2109, PAN: ZXCVB9876Q, transfer to user@okaxis",
        "Call 9123456789 or 09876543210 immediately regarding IFSC SBIN0001234",
        "Employee email admin@bank.gov.in with PAN QWERT1234Z",
    ]

    for raw in messy_inputs:
        tokenized = airlock.tokenize_text(raw, scope="batch_test")
        # Egress gate MUST accept the tokenized output without raising
        airlock.verify_egress(tokenized)
        assert airlock.egress.is_safe(tokenized) is True
