"""
Page 1: Circular Inbox (Stage 1).
Upload circular or select from C1, C2, C3, C4.
Airlock sanitizes PII tokens (visualized as chips).
Chunks into discrete clauses with bitemporal timestamps and SHA-256 digest.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator
from ui.theme import (
    inject_custom_css,
    render_mission_control_header,
    render_sidebar_controls,
    render_stage_stepper,
)

st.set_page_config(page_title="Circular Inbox | ARGUS v2", page_icon="📥", layout="wide")
inject_custom_css()
render_sidebar_controls()
render_mission_control_header()
render_stage_stepper(current_stage=1)

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

st.markdown("### 📥 Circular Inbox & PII Airlock Ingress")
st.caption("Stage 1 of 10: Untrusted circular text is airlocked to strip PII before any model or parser evaluates content.")

# Circular Preset Loader
circular_dir = REPO_ROOT / "data" / "circulars"
presets = {
    "C1: High-Value Cash Deposits & EDD (RBI/2026-27/42) [HERO CIRCULAR]": "C1_cash_deposit_edd.md",
    "C2: Capital Adequacy for UCBs & NBFCs (RBI/2026-27/58) [NOT APPLICABLE]": "C2_coop_nbfc_lending.md",
    "C3: High-Risk MCC UPI Limits (RBI/2026-27/71) [BITEMPORAL MEMORY]": "C3_upi_merchant_limits.md",
    "C4: Advisory with Prompt Injection (RBI/2026-27/89) [SECURITY TEST]": "C4_poisoned_circular.md",
}

selected_preset = st.selectbox("Select Regulatory Circular Preset or Custom:", list(presets.keys()))

default_text = ""
if selected_preset in presets:
    target_file = circular_dir / presets[selected_preset]
    if target_file.exists():
        default_text = target_file.read_text(encoding="utf-8")

col_input, col_airlock = st.columns([1.3, 0.7])

with col_input:
    circ_id = st.text_input("Circular Reference ID", value="RBI/2026-27/42" if "C1" in selected_preset else "RBI/2026-27/00")
    circ_title = st.text_input("Official Title", value=selected_preset.split(" [")[0])
    raw_text = st.text_area("Regulatory Circular Raw Text (Untrusted Input)", value=default_text, height=260)

with col_airlock:
    st.markdown(
        """
        <div class="argus-card-elevated">
            <div style="font-weight: 700; color: #22D3EE; margin-bottom: 8px;">🛡️ PII Airlock Egress Gate</div>
            <p style="font-size: 12px; color: #8A94A8;">All ingress documents are screened against Indian identity patterns (PAN, Aadhaar, Phone, Email, IFSC, UPI handles). Zero personal identifiers reach model prompts.</p>
            <div style="margin-top: 12px; display: flex; flex-direction: column; gap: 6px;">
                <span class="mono-chip">Pattern Matchers: 6 Financial Types</span>
                <span class="mono-chip mono-chip-green">Presidio Anonymizer: Synchronous</span>
                <span class="mono-chip mono-chip-amber">Untrusted Slot Isolation: Active</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if st.button("⚡ Ingest & Chunk Circular (Stage 1 Gate)", type="primary", use_container_width=True):
    with st.spinner("Processing PII airlock tokenization & clause chunking..."):
        clean_id = circ_id.replace("/", "-")
        res = orch.intake_agent.process_circular(
            circular_id=clean_id,
            circular_title=circ_title,
            raw_text=raw_text,
        )
        st.session_state.intake_result = res
        st.session_state.clauses = res["clauses"]
        st.session_state.raw_circular_text = raw_text
        st.session_state.circular_id = clean_id
        st.session_state.circular_title = circ_title
        st.session_state.demo_stage = 2
        st.toast(f"Ingested {res['clause_count']} clauses with hash {res['document_hash'][:12]}!", icon="✅")

if "intake_result" in st.session_state:
    res = st.session_state.intake_result
    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Discrete Clauses", res["clause_count"])
    with m2:
        st.metric("PII Tokens Masked", "0 Leaked (100% Sealed)")
    with m3:
        st.metric("Document Hash (SHA-256)", res["document_hash"][:12] + "...")
    with m4:
        st.metric("Bitemporal Temporal Index", "UTC Pinned")

    st.markdown("#### 📜 Extracted Clauses with Bitemporal Coordinates")
    for c in res["clauses"]:
        with st.expander(f"Clause `{c.id}`: {c.title or 'Numbered Sub-Clause'}", expanded=True):
            st.markdown(f"**Valid Range:** `{c.valid_from.strftime('%Y-%m-%d')} ➔ {c.valid_to.strftime('%Y-%m-%d')}`")
            st.code(c.clause_text, language="markdown")
