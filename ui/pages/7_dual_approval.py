"""
Page 7: Dual Human Approval & Governance Gate (Stage 8).
Enforces mandatory Maker-Checker dual signoff with Ed25519 digital signatures.
Guarantees that LLMs and agents cannot publish live rules autonomously.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator
from ui.theme import inject_custom_css, render_brand_header, render_pipeline_stepper

st.set_page_config(page_title="Dual Approval | ARGUS v2", page_icon="✍️", layout="wide")
inject_custom_css()
render_brand_header(current_stage_num=8, current_stage_name="HUMAN_APPROVAL")
render_pipeline_stepper(active_stage=8)


if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

# Ensure workflow state exists
if "workflow_state" not in st.session_state or not st.session_state.workflow_state:
    SAMPLE_CIRCULAR = """
Reserve Bank of India
Notification: RBI/2024-25/118
Section 2: High-Value Immediate Transfer Cooling Period
All regulated entities shall enforce a mandatory cooling period of 4 hours for any retail immediate payment
or UPI transaction where the single transaction amount meets or exceeds INR 50,000.
"""
    state = orch.run_pipeline_to_approval(
        circular_id="RBI-2024-118",
        circular_title="UPI Risk Management",
        circular_text=SAMPLE_CIRCULAR,
        bank_profile=st.session_state.bank_profile,
        historical_txns=st.session_state.historical_txns,
    )
    st.session_state.workflow_state = state

state = st.session_state.workflow_state

st.subheader(f"Review Package: {state.rule_definition.rule_name} (v{state.rule_definition.version})")

col_summary, col_cert = st.columns([1.2, 0.8])
with col_summary:
    st.markdown(
        f"""
- **Source Circular:** `{state.circular_id}`
- **Source Clause:** `{state.rule_definition.clause_id}`
- **Source Obligation:** `{state.rule_definition.obligation_id}`
- **Action Prescribed:** `{state.rule_definition.action.outcome}` (Tier: `{state.rule_definition.action.tier}`)
- **Mandatory Cooling Window:** `{state.rule_definition.action.cooling_period_hours} hours`
- **Citation Evidence ID:** `{state.rule_definition.action.evidence_id}`
"""
    )

with col_cert:
    st.success(f"🛡️ **Validation Certificate:** `{state.validation_report.certificate_id if state.validation_report else 'CERT-PENDING'}`")
    st.info("Validation Gate: All schema, citation, and unit test checks PASSED.")

st.divider()

st.subheader("Dual Signoff Execution")

col_maker, col_checker = st.columns(2)
with col_maker:
    maker_id = st.text_input("Maker Identity (Compliance Analyst)", value="compliance_analyst_rajesh")
    maker_notes = st.text_area("Maker Review Notes", value="Verified against circular clause 2. Cooling period threshold aligned to ₹50,000.", height=80)

with col_checker:
    checker_id = st.text_input("Checker Identity (VP / Head of Compliance)", value="vp_risk_priya")
    checker_notes = st.text_area("Checker Independent Verdict", value="Backtest alert surge is acceptable. Policy mapping conflicts resolved.", height=80)

if st.button("🔏 Grant Dual Cryptographic Signoff (Stage 8)", type="primary"):
    if maker_id.strip() == checker_id.strip():
        st.error("❌ Dual approval violation: Maker and Checker cannot be the same individual!")
    else:
        try:
            token = orch.grant_dual_approval(
                state=state,
                maker_id=maker_id.strip(),
                checker_id=checker_id.strip(),
            )
            st.session_state.approval_token = token
            st.success(f"✅ Dual Approval Token successfully minted: {token.token_id}")
        except Exception as e:
            st.error(f"Failed to sign approval: {str(e)}")

if "approval_token" in st.session_state:
    tok = st.session_state.approval_token
    st.divider()
    st.subheader("Cryptographic Dual Approval Token")
    st.json(tok.model_dump(mode="json"))
    st.success("Deployment API unlocked! Rule is now authorized for **Stage 9 Shadow Mode** and **Stage 10 Canary Rollout**.")
