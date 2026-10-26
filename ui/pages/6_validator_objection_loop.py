"""
Page 6: Validation Gate & Objection Loop (Stage 7).
Deterministic pass/fail gate for schema, conflict resolution, clause citations,
and synthetic tests. Demonstrates bounded re-routing loops on objection.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator
from ui.theme import inject_custom_css, render_brand_header, render_pipeline_stepper

st.set_page_config(page_title="Validation & Objection Loop | ARGUS v2", page_icon="⚖️", layout="wide")
inject_custom_css()
render_brand_header(current_stage_num=7, current_stage_name="VALIDATION_GATE")
render_pipeline_stepper(active_stage=7)


if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

st.markdown(
    """
### The 4 Deterministic Validation Gates
1. **Schema & OPA Compilation:** Syntactically valid Rego AST and Rule DSL.
2. **Conflict Resolution Check:** All active conflicts with system rules must be marked RESOLVED.
3. **100% Citation Coverage:** Every condition and action must cite a verified source clause `[CLAUSE:<ID>]`.
4. **Synthetic Unit Test Pass:** All positive and negative boundary test cases must execute successfully.
"""
)

col_mode, col_act = st.columns([1.2, 0.8])
with col_mode:
    test_mode = st.radio(
        "Demonstration Mode",
        ["Simulate Objection Loop (Iteration 1 Rejection ➔ Iteration 2 Pass)", "Validate Current Rule Definition"],
    )

with col_act:
    if st.button("⚖️ Run Stage 7 Validation Gate", type="primary"):
        SAMPLE_CIRCULAR = """
Reserve Bank of India
Notification: RBI/2024-25/118
Section 2: High-Value Immediate Transfer Cooling Period
All regulated entities shall enforce a mandatory cooling period of 4 hours for any retail immediate payment
or UPI transaction where the single transaction amount meets or exceeds INR 50,000.
"""
        with st.spinner("Executing Validation Gate & Objection Loop..."):
            state = orch.run_pipeline_to_approval(
                circular_id="RBI-2024-118",
                circular_title="UPI Risk Management",
                circular_text=SAMPLE_CIRCULAR,
                bank_profile=st.session_state.bank_profile,
                historical_txns=st.session_state.historical_txns,
                simulate_objection_loop="Simulate" in test_mode,
            )
            st.session_state.workflow_state = state
            st.session_state.validation_report = state.validation_report
        st.success("Validation Gate execution complete!")

if "validation_report" in st.session_state:
    val = st.session_state.validation_report
    state = st.session_state.get("workflow_state")
    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Verdict", "PASSED" if val.passed else "REJECTED")
    c2.metric("Citation Coverage", f"{val.citation_coverage_pct}%")
    c3.metric("Conflicts Checked", "PASS" if val.conflict_check_passed else "FAIL")
    c4.metric("Unit Tests Passed", f"{val.tests_passed}/{val.tests_total}")

    if state and state.objection_history:
        st.subheader("🔁 Objection Loop Re-Routing Trace")
        st.info("Demonstrates multi-agent collaboration: Validator rejected Iteration 1 draft; Orchestrator re-routed with actionable instructions.")
        
        for idx, obj in enumerate(state.objection_history, 1):
            st.markdown(
                f"""
                <div style="border: 2px solid #EF4444; border-radius: 8px; padding: 1rem; margin-bottom: 0.8rem; background-color: #FEF2F2;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 800; color: #991B1B; font-size: 1rem;">Objection {idx}: {obj.code.value}</span>
                        <span style="background-color: #EF4444; color: white; font-weight: 700; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">Re-routed to {obj.target_stage.value}</span>
                    </div>
                    <p style="color: #7F1D1D; margin-top: 0.5rem; font-size: 0.95rem;"><b>Critique:</b> {obj.message}</p>
                    <p style="color: #15803D; margin-top: 0.3rem; font-size: 0.9rem;"><b>Remediation Action:</b> {obj.suggested_fix}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if val.passed:
        st.success(f"🎉 **Deterministic Validation Certificate Issued:** `{val.certificate_id}`")
        st.markdown("All gates verified. Rule is now unlocked for **Stage 8 Human Approval**.")
    else:
        st.error("Validation failed. Rule cannot proceed to approval without remediation.")
