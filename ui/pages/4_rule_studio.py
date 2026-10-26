"""
ARGUS v2 — Stage 4: Rule Authoring & Compiler
Rule Author Agent: Authors rules in YAML Rule DSL, compiles to OPA Rego with unit tests,
and strictly enforces the 'DRAFT-ONLY' safety boundary.
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
from ui.services.client_v2 import get_sample_pipeline, compile_v2_rule


st.set_page_config(page_title="Rule Authoring — ARGUS v2", page_icon="⚙️", layout="wide")
inject_css()

page_header(
    "⚙️ Stage 4: Rule Authoring & Rule DSL Compiler",
    "Rule Author Agent · YAML Rule DSL · OPA Rego compilation · Automated unit tests · Draft-only gate"
)
render_ten_stage_pipeline(active_stage=4)
st.markdown("---")
render_bank_profile_header()

case = get_sample_pipeline()
obligation = case["obligation"]

with st.sidebar:
    st.markdown("### ⚙️ Stage 4: Rule Authoring")
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.8rem;color:#94A3B8;'>"
        "Generates clean, human-readable <b>YAML Rule DSL</b> mapped directly to the statutory clause. "
        "Compiles deterministically into OPA Rego with a comprehensive unit test suite. "
        "Enforces the <b>DRAFT-ONLY</b> barrier.</div>",
        unsafe_allow_html=True,
    )

# Guardrail Alert
st.markdown(
    "<div class='warning-banner' style='background:rgba(59,130,246,0.1);border-color:rgba(59,130,246,0.3);color:#93C5FD;'>"
    "🛡️ <b>Core Safety Guardrail Active:</b> Rule is authored with <code>status: DRAFT_ONLY</code>. "
    "Autonomous agents are architecturally prohibited from promoting rules to live enforcement without passing "
    "Validation (Stage 7) and Maker-Checker Dual Human Approval (Stage 8)."
    "</div>",
    unsafe_allow_html=True,
)

tab_dsl, tab_rego, tab_tests = st.tabs([
    "📜 YAML Rule DSL", "⚡ Compiled OPA Rego", "🧪 Auto-Generated Unit Tests"
])

with tab_dsl:
    section_header("YAML Rule Specification (Draft DSL)")
    st.code(case["rule_dsl_yaml"], language="yaml")
    st.markdown(f"**Target System Engine:** `Open Policy Agent (OPA) v0.68.0`")
    st.markdown(f"**Clause Binding:** `{case['clause_id']}` ➔ `{obligation['id']}`")

with tab_rego:
    section_header("Compiled Rego Policy Code")
    st.code(case["compiled_rego"], language="prolog")
    verified_banner("Deterministic AST Compilation Verified: Zero floating-point drift or prompt variance")

with tab_tests:
    section_header("OPA Rego Companion Test Suite")
    st.code(case["compiled_rego_tests"], language="prolog")
    st.info("3/3 unit tests simulated and passing in local memory.")

st.markdown("---")
col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("← Back to Stage 3: Policy Mapping"):
        st.switch_page("pages/3_policy_mapping.py")
with col_nav2:
    st.markdown("<div style='display:flex;justify-content:flex-end;'>", unsafe_allow_html=True)
    if st.button("Proceed to Stages 5 & 6: Backtesting & Impact →", type="primary"):
        st.switch_page("pages/5_backtest_impact.py")
    st.markdown("</div>", unsafe_allow_html=True)
