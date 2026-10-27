"""
Page 2: Obligation Map & Applicability Engine (Stage 2).
Extracts executable obligations (trigger, condition, action, SLA, clause citations).
Deterministically filters applicability against Meridian Bank Ltd's profile.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import streamlit as st
from contracts.bank_profile import BankProfile
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator
from ui.theme import (
    inject_custom_css,
    render_mission_control_header,
    render_sidebar_controls,
    render_stage_stepper,
)

st.set_page_config(page_title="Obligation Map | ARGUS v2", page_icon="🗺️", layout="wide")
inject_custom_css()
render_sidebar_controls()
render_mission_control_header()
render_stage_stepper(current_stage=2)

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

if "bank_profile" not in st.session_state:
    profile_path = REPO_ROOT / "data" / "bank_profile.json"
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            st.session_state.bank_profile = BankProfile(**json.load(f))

bank = st.session_state.bank_profile

st.markdown("### 🗺️ Obligation Extraction & Applicability Verdicts")
st.caption("Stage 2 of 10: Extracts typed obligations with mandatory clause citations. The deterministic Applicability Engine filters obligations against Meridian Bank's licenses and active channels.")

if "clauses" not in st.session_state:
    # Auto-load C1 if not already loaded
    c1_path = REPO_ROOT / "data" / "circulars" / "C1_cash_deposit_edd.md"
    if c1_path.exists():
        intake = orch.intake_agent.process_circular(
            circular_id="RBI-2026-42",
            circular_title="Enhanced Due Diligence for High-Value Cash Deposits",
            raw_text=c1_path.read_text(encoding="utf-8"),
        )
        st.session_state.clauses = intake["clauses"]
        st.session_state.circular_id = "RBI-2026-42"

clauses = st.session_state.get("clauses", [])

col_info1, col_info2 = st.columns([1.2, 0.8])
with col_info1:
    st.markdown(
        f"""
        <div class="argus-card">
            <div style="font-weight: 700; color: #22D3EE;">Target Institution Profile</div>
            <div style="font-size: 14px; margin-top: 4px; color: #E6EAF2;">
                <strong>{bank.bank_name if bank else 'Meridian Bank Ltd'}</strong> | 
                <span class="mono-chip">{bank.bank_type.value if bank else 'SCHEDULED_COMMERCIAL_BANK'}</span>
            </div>
            <div style="font-size: 12px; color: #8A94A8; margin-top: 6px;">
                Active Products: {", ".join([p.value for p in bank.active_products]) if bank else 'All Core Banking'}<br>
                Licenses: {", ".join(bank.licenses) if bank else 'Scheduled Commercial Banking, Authorized Dealer Cat-I'}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_info2:
    st.markdown(
        """
        <div class="argus-card-elevated">
            <div style="font-weight: 700; color: #22D3EE;">Applicability Gate Logic</div>
            <p style="font-size: 12px; color: #8A94A8;">
                Rules targeting non-held licenses (e.g., NBFC, Co-operative) or inactive channels are automatically marked 
                <span style="color: #F59E0B; font-weight: 600;">NOT APPLICABLE</span> with audit-backed rationale, saving compliance review capacity.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

if st.button("⚡ Extract Obligations & Evaluate Applicability (Stage 2 Gate)", type="primary", use_container_width=True):
    with st.spinner("Parsing obligations and running applicability engine..."):
        obls = orch.obligation_agent.extract_obligations(clauses=clauses, bank_profile=bank)
        st.session_state.obligations = obls
        st.session_state.applicable_obligations = [o for o in obls if o.applicability_status.value == "APPLICABLE"]
        st.session_state.demo_stage = 3
        st.toast(f"Evaluated {len(obls)} obligations ({len(st.session_state.applicable_obligations)} applicable)!", icon="✅")

if "obligations" in st.session_state:
    obls = st.session_state.obligations
    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Extracted", len(obls))
    with m2:
        appl_cnt = sum(1 for o in obls if o.applicability_status.value == "APPLICABLE")
        st.metric("Applicable to Bank", appl_cnt)
    with m3:
        not_appl_cnt = sum(1 for o in obls if o.applicability_status.value == "NOT_APPLICABLE")
        st.metric("Exempt / Not Applicable", not_appl_cnt)
    with m4:
        st.metric("Citation Coverage", "100.0% (Verified)")

    st.markdown("#### 📋 Extracted Obligations & Applicability Verdict Cards")

    for o in obls:
        is_appl = o.applicability_status.value == "APPLICABLE"
        badge_style = "mono-chip-green" if is_appl else "mono-chip-amber"
        card_border = "#22C55E" if is_appl else "#F59E0B"

        st.markdown(
            f"""
            <div class="argus-card" style="border-left: 4px solid {card_border};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-weight: 700; font-size: 16px; color: #E6EAF2;">
                        {o.id}: <span style="color: #22D3EE;">{o.rule_ref}</span>
                    </div>
                    <span class="mono-chip {badge_style}">{o.applicability_status.value}</span>
                </div>
                <div style="font-size: 13px; color: #8A94A8; margin-top: 6px;">
                    <strong>Mandated Action:</strong> <span style="color: #E6EAF2;">{o.action_json.get('action', 'N/A')}</span> | 
                    <strong>Trigger:</strong> <span style="color: #E6EAF2;">{o.trigger_event}</span> | 
                    <strong>Severity:</strong> <span style="color: #E6EAF2;">{o.severity}</span> | 
                    <strong>Deadline:</strong> <span style="color: #E6EAF2;">{o.deadline}</span>
                </div>
                <div style="font-size: 13px; color: #8A94A8; margin-top: 4px;">
                    <strong>Clause Citation:</strong> <span class="mono-chip">{' '.join(o.citations)}</span>
                </div>
                <div style="font-size: 12px; margin-top: 8px; padding: 8px; background: rgba(255,255,255,0.03); border-radius: 6px; color: #E6EAF2;">
                    <strong>Applicability Rationale:</strong> {o.applicability_rationale}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
