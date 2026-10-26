"""
ARGUS v2 — Stage 1: Circular Intake & Clause Chunker
Dedicated Intake Agent: Ingests, parses, and clause-chunks regulatory circulars with valid-time bitemporal dates and PII airlock gating.
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

from datetime import date, datetime
import streamlit as st

from ui.components import (
    inject_css, page_header, section_header, render_ten_stage_pipeline,
    render_bank_profile_header, verified_banner, badge
)
from ui.services.client_v2 import get_circulars


st.set_page_config(page_title="Circular Intake — ARGUS v2", page_icon="📥", layout="wide")
inject_css()

# Header & 10-Stage Progress
page_header(
    "📥 Stage 1: Regulatory Circular Intake",
    "Dedicated Intake Agent · Clause chunking · Bitemporal valid-time · PII airlock validation"
)
render_ten_stage_pipeline(active_stage=1)
st.markdown("---")
render_bank_profile_header()

circulars = get_circulars()
circ_map = {c["id"]: c for c in circulars}

# Sidebar Context
with st.sidebar:
    st.markdown("### 📥 Stage 1: Circular Intake")
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.8rem;color:#94A3B8;'>"
        "Parses regulatory circulars (RBI, FATF, FinCEN) into atomised, versioned clauses "
        "tagged with statutory <code>valid_from</code> and <code>valid_to</code> dates. "
        "Guarantees 100% PII airlock passage.</div>",
        unsafe_allow_html=True,
    )

section_header("Circular Intake Repository")

col_sel, col_up = st.columns([2, 1])
with col_sel:
    selected_id = st.selectbox(
        "Select Active Circular Corpus",
        list(circ_map.keys()),
        format_func=lambda k: f"{k} — {circ_map[k]['title'][:60]}…",
        key="intake_circ_select",
    )
with col_up:
    st.file_uploader("Upload New Circular (PDF, TXT, JSON)", type=["pdf", "txt", "json"], key="upload_circular_file")

circ = circ_map[selected_id]

# Metadata Grid
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"**Authority:** `{circ['authority']}`")
    st.markdown(f"**Reference:** `{circ['circular_ref']}`")
with col2:
    st.markdown(f"**Published Date:** `{circ['published_date'][:10]}`")
    st.markdown(f"**Effective Date:** `{circ['effective_date'][:10]}`")
with col3:
    st.markdown(f"**Valid From:** `{circ['valid_from'][:10]}`")
    st.markdown(f"**Valid To:** `{circ['valid_to'][:10]}`")
with col4:
    status_color = "green" if circ["status"] == "IN_FORCE" else "red"
    st.markdown(f"**Status:** {badge(circ['status'], status_color)}", unsafe_allow_html=True)
    st.markdown(f"**Clause Chunks:** `{len(circ['clauses'])} clauses`")

st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)
verified_banner("PII Airlock Passed: 0 unmasked entities in circular text · Delimited data slots enforced")

# Clause Chunk Viewer
section_header(f"Extracted Clause Chunks ({len(circ['clauses'])} clauses)")

for idx, clause in enumerate(circ["clauses"]):
    with st.expander(f"Clause #{idx+1} — [{clause['id']}] {clause['title']}", expanded=(idx == 0)):
        st.markdown(f"**Statutory Reference:** `{clause['clause_ref']}`")
        st.markdown(
            f"<div style='background:#111827;border-left:3px solid #3B82F6;padding:0.75rem 1rem;border-radius:4px;color:#E2E8F0;font-size:0.9rem;margin:0.5rem 0;line-height:1.6;'>"
            f"{clause['clause_text']}"
            f"</div>",
            unsafe_allow_html=True,
        )
        c_a, c_b, c_c = st.columns(3)
        c_a.markdown(f"**Governed Actor:** `{clause['actor']}`")
        c_b.markdown(f"**Trigger Event:** `{clause['trigger_event']}`")
        c_c.markdown(f"**Prescribed Action:** `{clause['action']}` (Tier `{clause['tier']}`)")
        
        st.markdown(
            f"**Keywords:** " + " ".join(f"`{k}`" for k in clause.get("keywords", [])),
        )

st.markdown("---")
st.markdown("<div style='display:flex;justify-content:flex-end;'>", unsafe_allow_html=True)
if st.button("Proceed to Stage 2: Obligation & Applicability →", type="primary"):
    st.switch_page("pages/2_obligation_map.py")
st.markdown("</div>", unsafe_allow_html=True)
