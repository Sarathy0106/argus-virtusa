"""
Unit Tests for LangGraph Cyclic State Graph Orchestrator.
Verifies:
1. End-to-end execution of StateGraph with MemorySaver checkpointer.
2. Applicability conditional routing (C2 not applicable -> terminates at obligations).
3. Applicable circular (C1) traversing all 10 stages through shadow rollout.
"""

import pytest

from contracts.bank_profile import BankProfile, BankType, ProductType
from contracts.deployment import DeploymentStage
from contracts.obligations import ApplicabilityStatus
from services.agents.broker import CapabilityBroker
from services.ledger.ledger import AuditLedger
from services.orchestrator.langgraph_orchestrator import ArgusLangGraphOrchestrator


SAMPLE_C1_TEXT = """
Reserve Bank of India
Notification: RBI/2024-25/118
Master Direction – Enhanced Risk Management Framework for Immediate and UPI Transactions

Section 1: Scope and Applicability
These directions apply to all Scheduled Commercial Banks and Payment System Operators operating UPI channels.

Section 2: High-Value Immediate Transfer Cooling Period
All regulated entities shall enforce a mandatory cooling period of 4 hours for any retail immediate payment
or UPI transaction where the single transaction amount meets or exceeds INR 50,000. During the cooling period,
the funds shall be held in escrow pending step-up multi-factor authentication or analytical clearance.
Effective deadline: w.e.f 2024-11-01.
"""

SAMPLE_C2_TEXT = """
Reserve Bank of India
Notification: RBI/2024-25/119
Prudential Framework – Capital Conservation Buffer for Urban Co-operative Banks and NBFCs

Section 1: Scope & Institutional Applicability
These directions apply exclusively to Primary (Urban) Co-operative Banks (UCBs) and NBFC entities. Scheduled Commercial Banks are exempt.

Section 2: Capital Conservation Buffer Mandate
All UCB and NBFC entities shall maintain an incremental Capital Conservation Buffer of 1.25 percent of risk-weighted assets.
"""


@pytest.fixture
def test_bank_profile() -> BankProfile:
    return BankProfile(
        bank_id="APEX_IN_001",
        bank_name="Apex Bank of India",
        bank_type=BankType.SCHEDULED_COMMERCIAL_BANK,
        licenses=["RETAIL_BANKING", "COMMERCIAL_BANKING", "PAYMENT_SYSTEM_OPERATOR"],
        active_products=[ProductType.UPI, ProductType.IMPS, ProductType.RETAIL_DEPOSITS],
        supported_channels=["UPI", "MOBILE", "NET_BANKING"],
        jurisdictions=["IN"],
    )


def test_langgraph_orchestrator_c1_flow(test_bank_profile):
    """Test full LangGraph StateGraph traversal with checkpointer for applicable circular."""
    ledger = AuditLedger()

    orchestrator = ArgusLangGraphOrchestrator(
        audit_ledger=ledger,
        deterministic=True,
    )

    final_state = orchestrator.run(
        circular_id="RBI-2024-118",
        circular_title="UPI Cooling Period Direction",
        circular_text=SAMPLE_C1_TEXT,
        bank_profile=test_bank_profile,
        thread_id="test_thread_c1",
    )

    assert final_state["current_stage"] == 9
    assert final_state["stage_name"] == "SHADOW_DEPLOYMENT"
    assert len(final_state["obligations"]) >= 1
    assert final_state["approval_token"] is not None
    assert final_state["deployment_stage"] == DeploymentStage.SHADOW


def test_langgraph_orchestrator_c2_non_applicable_flow(test_bank_profile):
    """Test LangGraph StateGraph early termination via conditional edge for non-applicable circular."""
    ledger = AuditLedger()

    orchestrator = ArgusLangGraphOrchestrator(
        audit_ledger=ledger,
        deterministic=True,
    )

    final_state = orchestrator.run(
        circular_id="RBI-2024-C2-NBFC",
        circular_title="NBFC CIC Capital Adequacy",
        circular_text=SAMPLE_C2_TEXT,
        bank_profile=test_bank_profile,
        thread_id="test_thread_c2",
    )

    # StateGraph should stop at stage 2 (OBLIGATION_EXTRACTION) via _route_applicability -> END
    assert final_state["current_stage"] == 2
    assert final_state["stage_name"] == "OBLIGATION_EXTRACTION"
    assert any(ob.applicability_status == ApplicabilityStatus.NOT_APPLICABLE for ob in final_state["obligations"])
    assert "deployment_stage" not in final_state
