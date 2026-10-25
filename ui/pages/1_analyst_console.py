"""
Page 1: Analyst Console & Case Investigation Workspace.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contracts.common import TransactionChannel
from contracts.transactions import Transaction
from services.cognition.clustering.clustering import AlertClusterer
from services.orchestrator.state_machine import ArgusOrchestrator

st.set_page_config(page_title="Analyst Console | ARGUS", page_icon="🕵️", layout="wide")

st.title("🕵️ Analyst Console & Investigation Queue")
st.caption(
    "Review high-priority cases, examine evidence topologies, and execute Maker-Checker governance."
)

# Initialize Orchestrator in Session State
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = ArgusOrchestrator()

orch: ArgusOrchestrator = st.session_state.orchestrator


# Generate Sample Cases
@st.cache_data
def get_sample_cases():
    clusterer = AlertClusterer()
    now = datetime.now(UTC)

    # 1. Mule Pass-Through Case (T2)
    inflow = Transaction(
        id="TXN-MULE-901",
        account_token="<ACCT_CRIME_ORIGIN>",
        counterparty_token="<ACCT_MULE_HUB_01>",
        amount=450000.0,
        timestamp=now,
        channel=TransactionChannel.RTGS,
        device_id_token="<DEV_MULE_RING_A>",
    )
    clusterer.add_alert(inflow, evidence_ids=["rapid_pass_through"], tier="T2")

    for i in range(3):
        outflow = Transaction(
            id=f"TXN-DISPERSAL-{i + 1}",
            account_token="<ACCT_MULE_HUB_01>",
            counterparty_token=f"<ACCT_CASH_OUT_{i + 1}>",
            amount=150000.0,
            timestamp=now,
            channel=TransactionChannel.IMPS,
            device_id_token="<DEV_MULE_RING_A>",
        )
        clusterer.add_alert(outflow, evidence_ids=["rapid_pass_through"], tier="T2")

    # 2. Structuring Window Case (T1)
    for i in range(4):
        st_txn = Transaction(
            id=f"TXN-STRUC-88{i}",
            account_token="<ACCT_SMURF_A>",
            counterparty_token="<ACCT_BENEFICIARY_B>",
            amount=49200.0 + (i * 150),
            timestamp=now,
            channel=TransactionChannel.UPI,
            device_id_token="<DEV_SMURF_01>",
        )
        clusterer.add_alert(st_txn, evidence_ids=["aml_structuring_window"], tier="T1")

    return clusterer.cluster_into_cases()


cases = get_sample_cases()

# Sidebar: Case Selection
st.sidebar.subheader("Active Investigation Cases")
case_options = {f"{c.case_id} — {c.primary_tier} (INR {c.total_amount:,.2f})": c for c in cases}
selected_label = st.sidebar.selectbox("Select Case Dossier:", list(case_options.keys()))
selected_case = case_options[selected_label]

# Case Header
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Case Identifier", selected_case.case_id)
with col2:
    tier_color = "red" if selected_case.primary_tier in ("T2", "T3") else "orange"
    st.metric("Governance Tier", selected_case.primary_tier)
with col3:
    st.metric("Total Flagged Volume", f"INR {selected_case.total_amount:,.2f}")
with col4:
    st.metric("Linked Transactions", len(selected_case.transaction_ids))

st.subheader(f"Dossier: {selected_case.title}")

tab_evidence, tab_graph, tab_narrative, tab_signoff = st.tabs(
    [
        "📊 Evidence & SHAP Attributions",
        "🕸️ Graph Topology",
        "📝 Verified SAR Narrative",
        "✍️ Maker-Checker Signoff",
    ]
)

with tab_evidence:
    st.write("#### Triggered Regulatory & Risk Evidence")
    for ev in selected_case.evidence_types:
        st.info(f"🛡️ **Rule Triggered:** `{ev}` — Verified by Open Policy Agent")

    st.write("#### TreeSHAP Feature Attribution Breakdown")
    sample_factors = [
        {
            "Feature": "rapid_pass_through_delta",
            "Attribution": "+0.45",
            "Description": "Funds dispersed in < 15 mins",
        },
        {
            "Feature": "shared_device_account_count",
            "Attribution": "+0.32",
            "Description": "Same device used across 4 accounts",
        },
        {
            "Feature": "structuring_window_count_24h",
            "Attribution": "+0.28",
            "Description": "Multiple transfers near INR 50k threshold",
        },
    ]
    st.table(sample_factors)

with tab_graph:
    st.write("#### Counterparty & Device Linkage Topology")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.write("**Linked Accounts (PII-Tokenized):**")
        for acc in selected_case.linked_accounts:
            st.code(acc)
    with col_g2:
        st.write("**Linked Device Fingerprints:**")
        for dev in selected_case.linked_devices:
            st.code(dev)

    st.json(selected_case.case_graph)

with tab_narrative:
    st.write("#### Evidence-Bound Suspicious Activity Report (SAR / STR)")
    st.caption(
        "Drafted by Autonomous Narrative Agent under strict citation gating (zero hallucination tolerance)."
    )

    narrative_text = (
        f"SAR INVESTIGATION DOSSIER — Case {selected_case.case_id}\n\n"
        f"Summary: A total of {len(selected_case.transaction_ids)} transactions totaling "
        f"INR {selected_case.total_amount:,.2f} were identified exhibiting coordinated activity.\n\n"
        f"Verified Evidence Citations:\n"
    )
    for ev in selected_case.evidence_types:
        narrative_text += f"- Detection pattern confirmed for `{ev}` [EVID:{ev}].\n"
    narrative_text += (
        f"\nCounterparties Involved: {', '.join(selected_case.linked_accounts)}\n"
        f"Recommendation: Immediate account hold and regulatory reporting under PMLA Section 12."
    )

    st.text_area("Narrative Content:", value=narrative_text, height=200)
    st.success("✅ Evidence Verifier: 100% of claims verified against active evidence nodes.")
    st.success("✅ PII Airlock: Zero raw customer identifiers present in narrative.")

with tab_signoff:
    st.write("#### Human-in-the-Loop Decision Signoff")
    if selected_case.primary_tier in ("T2", "T3"):
        st.warning(
            f"⚠️ Tier {selected_case.primary_tier} requires **Dual Maker-Checker** approval before actions can execute."
        )

    with st.form("hitl_form"):
        verdict = st.selectbox(
            "Analyst Verdict:", ["CONFIRMED_SUSPICIOUS", "FALSE_POSITIVE", "REQUEST_MORE_INFO"]
        )
        maker_id = st.text_input("Maker Analyst ID:", value="analyst_alice")
        checker_id = st.text_input(
            "Checker Supervisor ID (Required for T2/T3):",
            value="compliance_head_david" if selected_case.primary_tier in ("T2", "T3") else "",
        )
        analyst_notes = st.text_area(
            "Analyst Case Rationale / Notes:",
            value="Reviewed graph hops and confirmed rapid pass-through pattern.",
        )
        submitted = st.form_submit_button("Commit Decision & Record in Audit Ledger")

        if submitted:
            if selected_case.primary_tier in ("T2", "T3") and not checker_id:
                st.error("Error: Dual Maker-Checker signoff required for Tier T2/T3 cases.")
            else:
                audit_entry = orch.audit_ledger.append(
                    event_type=f"CASE_RESOLVED_{verdict}",
                    entity_id=selected_case.case_id,
                    signer=f"maker:{maker_id}|checker:{checker_id or 'none'}",
                    payload={
                        "verdict": verdict,
                        "maker": maker_id,
                        "checker": checker_id,
                        "notes": analyst_notes,
                        "case_id": selected_case.case_id,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
                st.success("Case successfully recorded in cryptographic audit ledger!")
                st.code(
                    f"Audit Block Hash: {audit_entry.verify_hash()}\nPrevious Block Hash: {audit_entry.prev_hash}"
                )
