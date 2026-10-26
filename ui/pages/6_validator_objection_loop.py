"""
ARGUS v2 — Stage 7: Validation Gate & Autonomous Objection Loop
Validator Agent: Performs 4-point verification (Schema, Coverage, Citations, Policy Conflicts).
Orchestrator Objection Loop: Re-routes rejected drafts back to Stages 3/4 with bounded iteration limits.
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
from ui.services.client_v2 import get_sample_pipeline


st.set_page_config(page_title="Validation & Objections — ARGUS v2", page_icon="🛡️", layout="wide")
inject_css()

page_header(
    "🛡️ Stage 7: Validation Gate & Objection Loop",
    "Validator Agent · 4-point compliance gate · Dynamic A2A objection routing · Iterative issue resolution"
)
render_ten_stage_pipeline(active_stage=7)
st.markdown("---")
render_bank_profile_header()

case = get_sample_pipeline()
history = case["validation_history"]

with st.sidebar:
    st.markdown("### 🛡️ Stage 7: Validation Gate")
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.8rem;color:#94A3B8;'>"
        "Validates AST schema, clause coverage, citation grounding, and absence of policy conflicts. "
        "<b>Autonomous Objection Loop:</b> When a conflict is detected, the Orchestrator re-routes "
        "the draft back to Stage 3/4 with specific evidence until it passes or hits max iterations (3).</div>",
        unsafe_allow_html=True,
    )

# Iteration Selector State
if "validator_sim_iteration" not in st.session_state:
    st.session_state["validator_sim_iteration"] = 1

curr_iter = st.session_state["validator_sim_iteration"]

col_t1, col_t2 = st.columns([2, 1])
with col_t1:
    section_header(f"Validation Engine — Current Run: Iteration {curr_iter} of 3")
with col_t2:
    if curr_iter == 1:
        if st.button("⚡ Trigger Agent Objection Loop & Auto-Fix ➔", type="primary"):
            st.session_state["validator_sim_iteration"] = 2
            st.toast("Orchestrator re-routed draft to Stage 4. Corrected rule authored and re-validated!")
            st.rerun()
    else:
        if st.button("🔄 Reset to Iteration 1 (Demonstrate Objection)"):
            st.session_state["validator_sim_iteration"] = 1
            st.rerun()

curr_data = history[0] if curr_iter == 1 else history[1]

# 4-Point Gate Status Grid
g1, g2, g3, g4 = st.columns(4)
with g1:
    s_col = "#34D399" if curr_data["schema_ok"] else "#EF4444"
    st.markdown(
        f"<div class='kpi-card'><div class='kpi-label'>1. YAML / Rego Schema</div>"
        f"<div class='kpi-value' style='color:{s_col};'>{'PASS ✓' if curr_data['schema_ok'] else 'FAIL ✗'}</div>"
        f"<div class='kpi-sub'>AST parsing check</div></div>",
        unsafe_allow_html=True,
    )
with g2:
    s_col = "#34D399" if curr_data["coverage_ok"] else "#EF4444"
    st.markdown(
        f"<div class='kpi-card'><div class='kpi-label'>2. Clause Coverage</div>"
        f"<div class='kpi-value' style='color:{s_col};'>{'PASS ✓' if curr_data['coverage_ok'] else 'FAIL ✗'}</div>"
        f"<div class='kpi-sub'>Mandate binding check</div></div>",
        unsafe_allow_html=True,
    )
with g3:
    s_col = "#34D399" if curr_data["citation_grounded"] else "#EF4444"
    st.markdown(
        f"<div class='kpi-card'><div class='kpi-label'>3. Citation Grounding</div>"
        f"<div class='kpi-value' style='color:{s_col};'>{'PASS ✓' if curr_data['citation_grounded'] else 'FAIL ✗'}</div>"
        f"<div class='kpi-sub'>Uncited claim rejection</div></div>",
        unsafe_allow_html=True,
    )
with g4:
    s_col = "#34D399" if curr_data["no_conflict_ok"] else "#EF4444"
    st.markdown(
        f"<div class='kpi-card'><div class='kpi-label'>4. Conflict Check</div>"
        f"<div class='kpi-value' style='color:{s_col};'>{'PASS ✓' if curr_data['no_conflict_ok'] else 'OBJECTION ⚠️'}</div>"
        f"<div class='kpi-sub'>Internal policy collision</div></div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

if curr_data["passed"]:
    verified_banner(
        f"Validation PASSED (Iteration {curr_iter}): All 4 verification gates satisfied. "
        "Rule is certified compliant and unlocked for Maker-Checker Approval (Stage 8)."
    )
else:
    warning_banner(
        f"Validation OBJECTION RAISED (Iteration {curr_iter}): Conflict detected with POL-LIMITS-RETAIL-04. "
        "Orchestrator activated A2A re-routing loop back to Stage 4 (Rule Authoring)."
    )

# Objection Trail Viewer
section_header("Validator Agent Diagnostic Trail")

if curr_data["objections"]:
    for obj in curr_data["objections"]:
        st.markdown(
            f"<div style='background:rgba(239,68,68,0.1);border-left:3px solid #EF4444;border-radius:4px;padding:0.8rem 1rem;color:#FCA5A5;font-size:0.88rem;margin-bottom:0.5rem;'>"
            f"<b>Validator Agent:</b> {obj}"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        f"<div style='background:#111827;border:1px solid #1E293B;border-radius:8px;padding:1rem;margin-top:0.5rem;'>"
        f"<div style='color:#60A5FA;font-weight:700;font-size:0.85rem;'>A2A ORCHESTRATOR RE-ROUTING ACTION:</div>"
        f"<div style='color:#CBD5E1;font-size:0.85rem;margin-top:0.25rem;'>"
        f"Re-routing payload to <code>{curr_data['re_route_stage']}</code> with conflict evidence. "
        f"Rule Author Agent instructed to inject account category scoping. "
        f"Bounded loop: attempt 1 of 3 (termination guaranteed)."
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"<div style='background:rgba(16,185,129,0.1);border-left:3px solid #10B981;border-radius:4px;padding:0.8rem 1rem;color:#6EE7B7;font-size:0.88rem;'>"
        f"<b>Validator Agent:</b> Re-authoring resolved all objections. Account category scoped to <code>['CORPORATE', 'AD_CAT1']</code>. "
        f"Retail daily limit ceiling unaffected. Zero policy conflicts remain."
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")
col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("← Back to Stages 5 & 6: Backtest"):
        st.switch_page("pages/5_backtest_impact.py")
with col_nav2:
    st.markdown("<div style='display:flex;justify-content:flex-end;'>", unsafe_allow_html=True)
    if curr_data["passed"]:
        if st.button("Proceed to Stage 8: Human Approval →", type="primary"):
            st.switch_page("pages/7_governance_approvals.py")
    else:
        st.button("Cannot Proceed: Validation Gate Locked 🔒", disabled=True)
    st.markdown("</div>", unsafe_allow_html=True)
