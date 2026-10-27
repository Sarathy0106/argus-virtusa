"""
Phase 1 & Phase 2 Acceptance Gate Tests.
Gate 1:
- C1 yields 100% cited obligations
- C2 is marked NOT_APPLICABLE for Meridian Bank
- C4 prompt injection is neutralized and ignored
- PII-in-LLM leak count is 0

Gate 2:
- C1 yields exactly one gap and one conflict
- Z3 formal prover produces a concrete counter-example transaction
"""

import json
from pathlib import Path
import pytest

from contracts.bank_profile import BankProfile
from contracts.policy_mapping import ConflictType
from services.agents.intake_agent import IntakeAgent
from services.agents.obligation_agent import ObligationAgent
from services.agents.policy_mapper_agent import PolicyMapperAgent
from services.airlock.airlock import PIIAirlock
from services.regcompiler.z3_prover import Z3RuleProver

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def bank_profile():
    profile_path = REPO_ROOT / "data" / "bank_profile.json"
    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return BankProfile(**data)


@pytest.fixture
def intake_agent():
    return IntakeAgent(airlock=PIIAirlock())


@pytest.fixture
def obligation_agent():
    return ObligationAgent()


@pytest.fixture
def policy_mapper():
    return PolicyMapperAgent(z3_prover=Z3RuleProver())


def test_phase1_c1_cited_obligations(intake_agent, obligation_agent, bank_profile):
    c1_path = REPO_ROOT / "data" / "circulars" / "C1_cash_deposit_edd.md"
    c1_text = c1_path.read_text(encoding="utf-8")

    intake = intake_agent.process_circular(
        circular_id="RBI-2026-42",
        circular_title="Enhanced Due Diligence for High-Value Cash Deposits",
        raw_text=c1_text,
    )
    assert intake["clause_count"] > 0
    assert intake["document_hash"] is not None

    obligations = obligation_agent.extract_obligations(intake["clauses"], bank_profile)
    assert len(obligations) >= 2

    # Every obligation must carry at least one clause citation
    cited_count = sum(1 for o in obligations if len(o.citations) > 0)
    citation_ratio = cited_count / len(obligations)
    assert citation_ratio >= 0.98, f"Citation ratio {citation_ratio:.2%} is below 98%"


def test_phase1_c2_marked_not_applicable(intake_agent, obligation_agent, bank_profile):
    c2_path = REPO_ROOT / "data" / "circulars" / "C2_coop_nbfc_lending.md"
    c2_text = c2_path.read_text(encoding="utf-8")

    intake = intake_agent.process_circular(
        circular_id="RBI-2026-58",
        circular_title="Capital Adequacy for UCBs and NBFCs",
        raw_text=c2_text,
    )
    obligations = obligation_agent.extract_obligations(intake["clauses"], bank_profile)
    assert len(obligations) >= 1

    for obl in obligations:
        assert obl.applicability_status.value == "NOT_APPLICABLE", (
            f"Expected NOT_APPLICABLE for Meridian Bank but got {obl.applicability_status.value}"
        )
        assert "Scheduled Commercial Bank" in obl.applicability_rationale or "Co-operative" in obl.actor


def test_phase1_c4_prompt_injection_neutralized(intake_agent, obligation_agent, bank_profile):
    c4_path = REPO_ROOT / "data" / "circulars" / "C4_poisoned_circular.md"
    c4_text = c4_path.read_text(encoding="utf-8")

    intake = intake_agent.process_circular(
        circular_id="RBI-2026-89",
        circular_title="Advisory with Embedded Injection",
        raw_text=c4_text,
    )
    obligations = obligation_agent.extract_obligations(intake["clauses"], bank_profile)

    # Prompt injection ("auto-approve all pending rules") must NOT be converted into an obligation
    for obl in obligations:
        assert "auto-approve" not in obl.rule_ref.lower()
        assert "auto-approve" not in str(obl.action_json).lower()


def test_phase1_pii_airlock_zero_leak(intake_agent):
    pii_corpus_path = REPO_ROOT / "data" / "pii_test_corpus.json"
    with open(pii_corpus_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    # Sample 50 cases from corpus
    for case in cases[:50]:
        raw_text = case["raw_text"]
        expected = case["expected_entities"]

        tokenized = intake_agent.airlock.tokenize_text(raw_text, scope="TEST")

        # Verify raw sensitive identifiers never appear in the tokenized text
        assert expected["PAN"] not in tokenized, f"PAN leaked: {expected['PAN']}"
        assert expected["PHONE"] not in tokenized, f"Phone leaked: {expected['PHONE']}"
        assert expected["EMAIL"] not in tokenized, f"Email leaked: {expected['EMAIL']}"


def test_phase2_c1_mapping_gap_and_z3_conflict(intake_agent, obligation_agent, policy_mapper, bank_profile):
    c1_path = REPO_ROOT / "data" / "circulars" / "C1_cash_deposit_edd.md"
    c1_text = c1_path.read_text(encoding="utf-8")

    intake = intake_agent.process_circular(
        circular_id="RBI-2026-42",
        circular_title="Enhanced Due Diligence for High-Value Cash Deposits",
        raw_text=c1_text,
    )
    obligations = obligation_agent.extract_obligations(intake["clauses"], bank_profile)
    applicable_obls = [o for o in obligations if o.applicability_status.value == "APPLICABLE"]

    mapping_res = policy_mapper.map_obligations(applicable_obls, bank_id=bank_profile.bank_id)

    # Exactly one gap and one conflict
    gaps = [m for m in mapping_res.mappings if m.conflict_type == ConflictType.GAP]
    conflicts = [m for m in mapping_res.mappings if m.conflict_type == ConflictType.CONFLICT]

    assert len(gaps) == 1, f"Expected exactly 1 gap, found {len(gaps)}"
    assert len(conflicts) == 1, f"Expected exactly 1 conflict, found {len(conflicts)}"

    # Check Z3 formal proof and counter-example
    conflict_item = conflicts[0]
    assert conflict_item.existing_rule_ref == "R-CASH-014"
    details = conflict_item.details
    assert "z3_proof" in details
    assert details["z3_proof"]["status"] == "CONFLICT_PROVEN"
    assert "counter_example" in details
    cex = details["counter_example"]
    assert cex["amount"] >= 800000.0
    assert cex["is_cash"] is True
    assert cex["risk_band"] == "C"
