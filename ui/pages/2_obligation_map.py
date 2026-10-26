"""
ARGUS v2 — Stage 2: Obligation Extraction & Bank Applicability Engine
Obligation Agent: Extracts structured obligations and determines institutional applicability against the Bank Profile.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
UI_ROOT = Path(__file__).resolve().parent.parent

if str(UI_ROOT) in sys.path:
    sys.path.remove(str(UI_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
elif sys.path[0] != str(REPO_ROOT):
    sys.path.remove(str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from ui.components import (
    inject_css, page_header, section_header, render_ten_stage_pipeline,
    render_bank_profile_header, verified_banner, warning_banner, badge
)
from ui.services.client_v2 import (
    get_active_bank_profile, get_sample_pipeline, evaluate_applicability
)


st.set_page_config(page_title="Obligation & Applicability — ARGUS v2", page_icon="⚖️", layout="wide")
inject_css()

page_header(
    "⚖️ Stage 2: Obligation Extraction & Bank Applicability",
    "Obligation Agent · Structured registry · Institutional profile filtering · Statutory deadlines"
)
render_ten_stage_pipeline(active_stage=2)
st.markdown("---")
render_bank_profile_header()

case = get_sample_pipeline()
obligation = case["obligation"]
active_bank = get_active_bank_profile()

with st.sidebar:
    st.markdown("### ⚖️ Stage 2: Obligation Registry")
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.8rem;color:#94A3B8;'>"
        "Translates legal text into machine-executable obligation contracts (actor, condition, action, deadline). "
        "<b>Applicability Engine</b> checks whether this institution holds the required licenses and products.</div>",
        unsafe_allow_html=True,
    )

# Run Applicability Check against current bank profile
applicability = evaluate_applicability(obligation, active_bank)

section_header("Institutional Applicability Determination")

if applicability.is_applicable:
    st.markdown(
        f"<div class='verified-banner' style='padding:1rem 1.25rem;'>"
        f"<div style='font-size:1.4rem;margin-right:0.5rem;'>✅</div>"
        f"<div>"
        f"<div style='font-weight:700;font-size:1rem;color:#34D399;'>STATUS: APPLICABLE TO {active_bank['name'].upper()}</div>"
        f"<div style='color:#CBD5E1;font-size:0.88rem;margin-top:0.25rem;'>{applicability.reason}</div>"
        f"<div style='color:#FCD34D;font-size:0.8rem;margin-top:0.35rem;font-weight:600;'>Statutory Compliance Deadline: {applicability.statutory_deadline}</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"<div class='warning-banner' style='padding:1rem 1.25rem;'>"
        f"<div style='font-size:1.4rem;margin-right:0.5rem;'>🚫</div>"
        f"<div>"
        f"<div style='font-weight:700;font-size:1rem;color:#FBBF24;'>STATUS: NOT APPLICABLE TO {active_bank['name'].upper()}</div>"
        f"<div style='color:#CBD5E1;font-size:0.88rem;margin-top:0.25rem;'>{applicability.reason}</div>"
        f"<div style='color:#94A3B8;font-size:0.8rem;margin-top:0.35rem;'>Action: Obligation suppressed from IT rule generation pipeline for this bank.</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

# Obligation Details
section_header(f"Obligation Registry Entry [{obligation['id']}]")

col_a, col_b = st.columns(2)
with col_a:
    st.markdown(f"**Obligation ID:** `{obligation['id']}`")
    st.markdown(f"**Source Clause Reference:** `{obligation['clause_id']}`")
    st.markdown(f"**Regulated Actor:** `{obligation['actor']}`")
    st.markdown(f"**Trigger Event:** `{obligation['trigger_event']}`")
    st.markdown(f"**Statutory Deadline:** `{obligation['statutory_deadline']}`")

with col_b:
    st.markdown(f"**Rule Identifier:** `{obligation['rule_ref']}`")
    st.markdown(f"**Governance Tier:** {badge(obligation['action_json']['tier'], 'red')}", unsafe_allow_html=True)
    st.markdown(f"**Prescribed Action:** `{obligation['action_json']['action']}`")
    st.markdown(f"**Severity:** {badge(obligation['severity'], 'red')}", unsafe_allow_html=True)

st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

tab_cond, tab_act, tab_json = st.tabs(["📋 Machine Conditions", "⚡ Prescribed Actions", "🔍 Raw JSON Contract"])
with tab_cond:
    st.json(obligation["condition_json"])
with tab_act:
    st.json(obligation["action_json"])
with tab_json:
    st.json(obligation)

st.markdown("---")
col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("← Back to Stage 1: Circular Intake"):
        st.switch_page("pages/1_circular_inbox.py")
with col_nav2:
    st.markdown("<div style='display:flex;justify-content:flex-end;'>", unsafe_allow_html=True)
    if st.button("Proceed to Stage 3: Policy Mapping →", type="primary"):
        st.switch_page("pages/3_policy_mapping.py")
    st.markdown("</div>", unsafe_allow_html=True)
