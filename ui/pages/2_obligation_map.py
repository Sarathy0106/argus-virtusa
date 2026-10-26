"""
Page 2: Obligation Registry & Bank Profile Applicability Engine (Stage 2).
Extracts executable obligations from clauses and deterministically filters
them against the institution profile (licenses, active products, channels).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from contracts.bank_profile import BankProfile, BankType, ProductType
from contracts.obligations import ApplicabilityStatus
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator
from ui.theme import inject_custom_css, render_brand_header, render_pipeline_stepper

st.set_page_config(page_title="Obligation Map | ARGUS v2", page_icon="🗺️", layout="wide")
inject_custom_css()
render_brand_header(current_stage_num=2, current_stage_name="OBLIGATION_EXTRACTION")
render_pipeline_stepper(active_stage=2)


if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

# Bank Profile Selector
st.sidebar.subheader("Institution Profile")
bank_choice = st.sidebar.selectbox(
    "Active Profile",
    ["Apex Bank of India (Scheduled Commercial Bank)", "Metro Payments Bank (Payments Bank)", "Gramin Cooperative Bank (Rural Coop)"],
)

if "Apex" in bank_choice:
    profile = BankProfile(
        bank_id="APEX_IN_001",
        bank_name="Apex Bank of India",
        bank_type=BankType.SCHEDULED_COMMERCIAL_BANK,
        licenses=["RETAIL_BANKING", "COMMERCIAL_BANKING", "PAYMENT_SYSTEM_OPERATOR", "FOREX_AD_CAT1"],
        active_products=[ProductType.UPI, ProductType.IMPS, ProductType.RTGS, ProductType.CREDIT_CARD],
        supported_channels=["UPI", "MOBILE", "NET_BANKING", "ATM", "BRANCH"],
    )
elif "Metro" in bank_choice:
    profile = BankProfile(
        bank_id="METRO_PAY_042",
        bank_name="Metro Payments Bank",
        bank_type=BankType.PAYMENTS_BANK,
        licenses=["PAYMENT_SYSTEM_OPERATOR", "RETAIL_BANKING"],
        active_products=[ProductType.UPI, ProductType.IMPS],
        supported_channels=["UPI", "MOBILE"],
    )
else:
    profile = BankProfile(
        bank_id="GRAMIN_COOP_099",
        bank_name="Gramin Cooperative Bank",
        bank_type=BankType.COOPERATIVE_BANK,
        licenses=["RETAIL_BANKING"],
        active_products=[ProductType.RETAIL_DEPOSITS],
        supported_channels=["BRANCH"],
    )

st.session_state.bank_profile = profile

# Ensure clauses are loaded
if "clauses" not in st.session_state:
    SAMPLE_CIRCULAR = """
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

Section 3: High-Value Cross-Border RTGS Outflows
All Scheduled Commercial Banks facilitating outbound cross-border RTGS payments exceeding INR 500,000
must perform real-time sanction checks and secondary compliance officer clearance.
Effective deadline: w.e.f 2024-12-31.
"""
    intake = orch.intake_agent.process_circular("RBI-2024-118", "UPI Risk Management", SAMPLE_CIRCULAR)
    st.session_state.clauses = intake["clauses"]

col_inst, col_action = st.columns([1.2, 0.8])
with col_inst:
    st.info(
        f"**Evaluating For:** `{profile.bank_name}` | **Type:** `{profile.bank_type.value}`\n\n"
        f"**Active Products:** `{', '.join([p.value for p in profile.active_products])}` | "
        f"**Channels:** `{', '.join(profile.supported_channels)}`"
    )

with col_action:
    if st.button("🔍 Extract & Filter Obligations (Stage 2)", type="primary"):
        with st.spinner("Extracting obligations and running Applicability Engine..."):
            obligations = orch.obligation_agent.extract_obligations(st.session_state.clauses, profile)
            st.session_state.obligations = obligations
        st.success(f"Evaluated {len(obligations)} obligations against {profile.bank_name}!")

if "obligations" in st.session_state:
    obls = st.session_state.obligations
    app_count = sum(1 for o in obls if o.applicability_status == ApplicabilityStatus.APPLICABLE)
    non_app_count = len(obls) - app_count

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Obligations Extracted", len(obls))
    c2.metric("Applicable to this Bank", app_count)
    c3.metric("Filtered Out (Not Applicable)", non_app_count)

    st.subheader("Obligation Registry & Applicability Table")
    for obl in obls:
        is_app = obl.applicability_status == ApplicabilityStatus.APPLICABLE
        status_color = "#10B981" if is_app else "#EF4444"
        badge = "APPLICABLE" if is_app else "NOT APPLICABLE"

        with st.container():
            st.markdown(
                f"""
                <div style="border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; margin-bottom: 0.8rem; background-color: #FAFAFA;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; font-size: 1.1rem; color: #1E293B;">{obl.id} (Clause: {obl.clause_id})</span>
                        <span style="background-color: {status_color}20; color: {status_color}; font-weight: 800; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.8rem;">{badge}</span>
                    </div>
                    <p style="margin-top: 0.5rem; color: #475569; font-size: 0.95rem;"><b>Applicability Rationale:</b> {obl.applicability_rationale}</p>
                    <div style="display: flex; gap: 1.5rem; font-size: 0.85rem; color: #64748B;">
                        <span><b>Actor:</b> {obl.actor}</span>
                        <span><b>Channel:</b> {obl.condition_json.get('channel', 'N/A')}</span>
                        <span><b>Deadline:</b> {obl.deadline or 'Immediate'}</span>
                        <span><b>Severity:</b> {obl.severity}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander(f"View Technical Schema & Conditions for {obl.id}"):
                c_left, c_right = st.columns(2)
                with c_left:
                    st.write("**Machine-Readable Conditions:**")
                    st.json(obl.condition_json)
                with c_right:
                    st.write("**Prescribed Action & Tier:**")
                    st.json(obl.action_json)
                    st.write(f"**Citations:** `{', '.join(obl.citations)}`")
