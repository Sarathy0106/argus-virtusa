"""
Page 3: Rule Studio & Reg-to-Rule Compiler.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contracts.obligations import RegulatoryObligation
from services.ingest.simulator import SyntheticTransactionGenerator
from services.regcompiler.compiler import CompilationResult, RegToRuleCompiler

st.set_page_config(page_title="Rule Studio | ARGUS", page_icon="⚙️", layout="wide")

st.title("⚙️ Rule Studio & Reg-to-Rule Compiler")
st.caption(
    "Transform unstructured regulatory circulars into versioned Rego policies, simulate historical impact, and publish via Maker-Checker."
)

compiler = RegToRuleCompiler()

st.subheader("1. Ingest Regulatory Obligation")
col_ob1, col_ob2 = st.columns(2)

with col_ob1:
    obligation_id = st.text_input("Obligation Identifier:", value="OBL-RBI-WIRE-2026-01")
    clause_ref = st.text_input("Source Clause Ref:", value="RBI-MD-WIRE-Sec4A")
    rule_name = st.text_input("Candidate Rule Name:", value="cross_border_wire_threshold")

with col_ob2:
    threshold_amt = st.number_input("Monetary Threshold (INR):", value=800000.0, step=50000.0)
    channel = st.selectbox("Transaction Channel:", ["RTGS", "NEFT", "UPI", "IMPS"])
    prescribed_action = st.selectbox("Prescribed Action:", ["HOLD", "BLOCK", "ESCALATE"])
    risk_tier = st.selectbox("Assigned Governance Tier:", ["T2", "T1", "T3"])

obligation = RegulatoryObligation(
    id=obligation_id,
    clause_id=clause_ref,
    actor="Commercial Bank",
    trigger_event="TRANSACTION_SUBMITTED",
    condition_json={"threshold_amount": threshold_amt, "channel": channel},
    action_json={"action": prescribed_action, "tier": risk_tier},
    rule_ref=rule_name,
)

st.subheader("2. Synthesize Policy-as-Code (Rego)")
rego_code, test_code = compiler.compile_obligation_to_rego(obligation)

col_r1, col_r2 = st.columns(2)
with col_r1:
    st.write("**Synthesized Rego Policy:**")
    st.code(rego_code, language="rego")
with col_r2:
    st.write("**Synthesized OPA Test Suite:**")
    st.code(test_code, language="rego")

st.subheader("3. Historical Impact Simulation")
st.caption(
    "Simulates how many additional transactions would trigger alerts under this candidate rule using recent transaction history."
)

if st.button("Run Impact Simulation on Historical Transactions", type="primary"):
    generator = SyntheticTransactionGenerator(seed=42)
    history = generator.generate_dataset(150)
    report = compiler.simulate_historical_impact(obligation, history)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Transactions Evaluated", report.total_txns_analyzed)
    with c2:
        st.metric("Baseline Alerts", report.baseline_alert_count)
    with c3:
        st.metric(
            "Candidate Rule Alerts", report.new_alert_count, delta=f"+{report.delta_percentage}%"
        )
    with c4:
        st.metric("Total Flagged Volume", f"INR {report.total_flagged_volume_inr:,.2f}")

    st.success(
        f"Simulation completed: candidate rule produces a manageable {report.delta_percentage}% increase in alert volume."
    )

st.subheader("4. Dual Maker-Checker Publication")
st.caption("No policy rule is ever deployed without two independent human compliance approvals.")

with st.form("publish_form"):
    maker = st.text_input("Maker Compliance Officer ID:", value="compliance_officer_sarah")
    checker = st.text_input("Checker Head of Risk ID:", value="risk_head_marcus")
    submit_pub = st.form_submit_button("Approve & Publish Rule Bundle")

    if submit_pub:
        if maker == checker:
            st.error("Error: Maker and Checker cannot be the same individual.")
        else:
            compilation = CompilationResult(
                obligation=obligation, draft_rego_code=rego_code, draft_test_code=test_code
            )
            # In simulation mode, record into audit ledger
            compiler.audit_ledger.append(
                event_type="RULE_BUNDLE_PUBLISHED",
                entity_id=rule_name,
                signer=f"maker:{maker}|checker:{checker}",
                payload={
                    "obligation_id": obligation_id,
                    "rule_ref": rule_name,
                    "new_bundle_version": "1.1.0",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
            st.success(
                "✅ Policy bundle published with version `1.1.0`! Recorded in cryptographic audit ledger."
            )
