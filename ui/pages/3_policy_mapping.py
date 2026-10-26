"""
ARGUS v2 — Stage 3: Policy Mapping & Gap Analysis
Policy Mapper Agent: Maps statutory obligations to internal policies and live system rules;
detects Gaps, Overlaps, and Conflicts before rule authoring.
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
import pandas as pd

from ui.components import (
    inject_css, page_header, section_header, render_ten_stage_pipeline,
    render_bank_profile_header, verified_banner, warning_banner,
    badge, mapping_type_pill
)
from ui.services.client_v2 import get_sample_pipeline, run_policy_mapping


st.set_page_config(page_title="Policy Mapping — ARGUS v2", page_icon="🗺️", layout="wide")
inject_css()

page_header(
    "🗺️ Stage 3: Internal Policy Mapping & Gap Detection",
    "Policy Mapper Agent · Traceability graph · Gap identification · Overlap and conflict detection"
)
render_ten_stage_pipeline(active_stage=3)
st.markdown("---")
render_bank_profile_header()

case = get_sample_pipeline()
obligation = case["obligation"]
mappings = case["policy_mapping"]

with st.sidebar:
    st.markdown("### 🗺️ Stage 3: Policy Mapping")
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.8rem;color:#94A3B8;'>"
        "Connects external obligations with the bank's internal policy inventory. "
        "Flags operational <b>Gaps</b> (unregulated blindspots) and <b>Conflicts</b> "
        "(incompatible limits) before any code is generated.</div>",
        unsafe_allow_html=True,
    )

# Visual Traceability Banner
section_header("End-to-End Traceability Path")
st.markdown(
    f"<div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1rem 1.25rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;'>"
    f"<div><span style='color:#94A3B8;font-size:0.75rem;font-weight:700;'>1. CIRCULAR CLAUSE</span><br><code style='color:#60A5FA;font-weight:700;'>{case['clause_id']}</code></div>"
    f"<div style='color:#475569;'>➔</div>"
    f"<div><span style='color:#94A3B8;font-size:0.75rem;font-weight:700;'>2. OBLIGATION ID</span><br><code style='color:#A855F7;font-weight:700;'>{obligation['id']}</code></div>"
    f"<div style='color:#475569;'>➔</div>"
    f"<div><span style='color:#94A3B8;font-size:0.75rem;font-weight:700;'>3. INTERNAL POLICY</span><br><code style='color:#FBBF24;font-weight:700;'>POL-WIRE-INTL-01</code></div>"
    f"<div style='color:#475569;'>➔</div>"
    f"<div><span style='color:#94A3B8;font-size:0.75rem;font-weight:700;'>4. LIVE SYSTEM RULE</span><br><code style='color:#34D399;font-weight:700;'>RULE-LEGACY-WIRE-01 (v1.0.0)</code></div>"
    f"</div>",
    unsafe_allow_html=True,
)

st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

# Gaps & Conflicts Summary
gap_count = sum(1 for m in mappings if m["mapping_type"] == "GAP")
conflict_count = sum(1 for m in mappings if m["mapping_type"] == "CONFLICT")

col1, col2 = st.columns(2)
with col1:
    warning_banner(f"Detected {gap_count} Regulatory Gap: Existing threshold leaves transactions ₹800k–₹1M unmonitored")
with col2:
    st.markdown(
        f"<div class='warning-banner' style='border-color:rgba(239,68,68,0.4);background:rgba(239,68,68,0.1);color:#FCA5A5;'>"
        f"⚠️ Detected {conflict_count} Policy Conflict: Candidate wire threshold clashes with retail limit ₹500k"
        f"</div>",
        unsafe_allow_html=True,
    )

section_header("Policy Mapping Inventory & Findings")

for idx, m in enumerate(mappings):
    mtype = m["mapping_type"]
    pill_html = mapping_type_pill(mtype)
    
    with st.expander(f"Finding #{idx+1} — {m['internal_policy_id']}: {m['internal_policy_title']} [{mtype}]", expanded=True):
        st.markdown(f"**Classification:** {pill_html}", unsafe_allow_html=True)
        st.markdown(f"**Existing System Rule:** `{m['existing_rule_ref']}` (Current Threshold: ₹{m['existing_threshold']:,.0f})")
        st.markdown(f"**Proposed Statutory Threshold:** `₹{m['proposed_threshold']:,.0f}`")
        
        st.markdown(
            f"<div style='background:#131B2E;border:1px solid #1E293B;border-radius:6px;padding:0.85rem;margin:0.5rem 0;color:#CBD5E1;font-size:0.88rem;line-height:1.6;'>"
            f"<b>Details:</b> {m['conflict_detail']}<br>"
            f"<b style='color:#60A5FA;'>Recommended Remediation:</b> {m['suggested_action']}"
            f"</div>",
            unsafe_allow_html=True,
        )

st.markdown("---")
col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("← Back to Stage 2: Obligation & Applicability"):
        st.switch_page("pages/2_obligation_map.py")
with col_nav2:
    st.markdown("<div style='display:flex;justify-content:flex-end;'>", unsafe_allow_html=True)
    if st.button("Proceed to Stage 4: Rule Authoring →", type="primary"):
        st.switch_page("pages/4_rule_studio.py")
    st.markdown("</div>", unsafe_allow_html=True)
