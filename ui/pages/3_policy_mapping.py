"""
Page 3: Policy & Rule Mapping (Stage 3).
Maps extracted obligations to internal bank policies and existing system rules.
Detects Gaps, Overlaps, and actively conflicting rules, providing remediation options.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from contracts.policy_mapping import ConflictStatus, ConflictType
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator
from ui.theme import inject_custom_css, render_brand_header, render_pipeline_stepper

st.set_page_config(page_title="Policy Mapping | ARGUS v2", page_icon="🧭", layout="wide")
inject_custom_css()
render_brand_header(current_stage_num=3, current_stage_name="POLICY_MAPPING")
render_pipeline_stepper(active_stage=3)


if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

# Ensure obligations are extracted
if "obligations" not in st.session_state:
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
    st.session_state.obligations = orch.obligation_agent.extract_obligations(
        st.session_state.clauses, st.session_state.bank_profile
    )

applicable_obls = [o for o in st.session_state.obligations if o.applicability_status.value == "APPLICABLE"]

if st.button("🔎 Run Policy & Rule Mapping Analysis (Stage 3)", type="primary"):
    with st.spinner("Analyzing rules catalog and detecting conflicts..."):
        res = orch.policy_mapper_agent.map_obligations(
            applicable_obls, bank_id=st.session_state.bank_profile.bank_id
        )
        st.session_state.policy_mapping = res
    st.success(f"Mapping analysis complete: {res.unresolved_conflicts} conflicts and {res.unresolved_gaps} gaps identified.")

if "policy_mapping" in st.session_state:
    mapping_res = st.session_state.policy_mapping
    st.divider()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Mappings Analyzed", len(mapping_res.mappings))
    c2.metric("Active Conflicts Detected", mapping_res.unresolved_conflicts)
    c3.metric("Regulatory Gaps (Missing Rules)", mapping_res.unresolved_gaps)

    st.subheader("Mapping Results & Conflict Details")

    for m in mapping_res.mappings:
        is_conflict = m.conflict_type == ConflictType.CONFLICT
        badge_color = "#EF4444" if is_conflict else "#F59E0B"
        status_color = "#10B981" if m.status == ConflictStatus.RESOLVED else "#EF4444"

        with st.container():
            st.markdown(
                f"""
                <div style="border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; background-color: #FFFFFF;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; font-size: 1.1rem; color: #0F172A;">Mapping {m.mapping_id}: Obligation {m.obligation_id}</span>
                        <div>
                            <span style="background-color: {badge_color}20; color: {badge_color}; font-weight: 800; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.8rem; margin-right: 0.5rem;">{m.conflict_type.value}</span>
                            <span style="background-color: {status_color}20; color: {status_color}; font-weight: 800; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.8rem;">{m.status.value}</span>
                        </div>
                    </div>
                    <p style="margin-top: 0.6rem; color: #334155; font-size: 0.95rem;">{m.description}</p>
                    <div style="background-color: #F8FAFC; border-left: 4px solid #3B82F6; padding: 0.6rem 1rem; border-radius: 4px; margin-top: 0.5rem;">
                        <span style="font-size: 0.85rem; color: #1E40AF; font-weight: 600;">Recommended Fix:</span>
                        <span style="font-size: 0.85rem; color: #1E293B; margin-left: 0.3rem;">{m.suggested_resolution}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if is_conflict and m.status == ConflictStatus.DETECTED:
                col_btn, _ = st.columns([0.4, 0.6])
                with col_btn:
                    if st.button(f"⚡ Resolve Conflict for {m.mapping_id}", key=f"btn_res_{m.mapping_id}"):
                        orch.policy_mapper_agent.resolve_mapping_conflict(m, resolution_choice="LOWER_LIMIT_AND_ADD_COOLING")
                        mapping_res.compute_summary()
                        st.success(f"Conflict {m.mapping_id} marked as RESOLVED. Rule Author Agent will incorporate fixes.")
                        st.rerun()
