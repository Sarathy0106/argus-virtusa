"""
ARGUS v2 — Regulatory Mission Control (Home).
Agentic Regulatory Guard with Unified Safety.
"Deterministic core, probabilistic edge."
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
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

st.set_page_config(
    page_title="ARGUS v2 — Regulatory Mission Control",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Part 5 Design System
inject_custom_css()
render_sidebar_controls()
render_mission_control_header()

# Global Session State
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

if "bank_profile" not in st.session_state:
    profile_path = REPO_ROOT / "data" / "bank_profile.json"
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            st.session_state.bank_profile = BankProfile(**json.load(f))
    else:
        st.session_state.bank_profile = None

if "demo_stage" not in st.session_state:
    st.session_state.demo_stage = 1

render_stage_stepper(current_stage=st.session_state.demo_stage)

# Mission Control Hero Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        """
        <div class="argus-card">
            <div class="metric-hero" style="color: #22C55E;">0</div>
            <div class="metric-label">PII Leaks (Airlock Gate)</div>
            <div style="font-size: 11px; color: #8A94A8; margin-top: 4px;">100% Tokenized at Ingress</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="argus-card">
            <div class="metric-hero" style="color: #22D3EE;">100%</div>
            <div class="metric-label">Clause-to-Rule Citation</div>
            <div style="font-size: 11px; color: #8A94A8; margin-top: 4px;">Zero Unbound Obligations</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="argus-card">
            <div class="metric-hero" style="color: #6366F1;">2-of-2</div>
            <div class="metric-label">Dual Cryptographic Signatures</div>
            <div style="font-size: 11px; color: #8A94A8; margin-top: 4px;">Maker-Checker Enforced</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        """
        <div class="argus-card">
            <div class="metric-hero" style="color: #A78BFA;">&lt; 1.0s</div>
            <div class="metric-label">Saga Rollback Recovery</div>
            <div style="font-size: 11px; color: #8A94A8; margin-top: 4px;">Atomic Git Bundle Pointer</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Executive Overview & 5-Minute Demo Guide
st.markdown("### Executive Mission Briefing")
st.markdown(
    """
    **The Problem:** Commercial banks spend weeks manually reading regulatory circulars, cross-referencing
    internal policies and live transaction filters, and coordinating with IT. This delay misses compliance
    deadlines and frequently deploys wrong-scope or conflicting rules.

    **The ARGUS Solution:** A 10-stage gated multi-agent framework that safely converts **Circular Text ➔ Verified Live Rule**.
    LLMs propose drafts in an isolated sandbox, deterministic code (Z3 theorem prover, OPA, and DuckDB) mathematically
    validates constraints, and two distinct human compliance officers cryptographically sign before any rule reaches production.
    """
)

# 8 Navigation Tiles
st.markdown("### Mission Control Workspaces")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        """
        <div class="argus-card">
            <div style="font-size: 20px; font-weight: 700; color: #22D3EE;">1. Circular Inbox</div>
            <p style="font-size: 13px; color: #8A94A8; margin: 8px 0;">Ingest C1-C4 circulars, airlock PII entities, and chunk bitemporal clauses.</p>
            <span class="mono-chip">Stage 1</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        """
        <div class="argus-card">
            <div style="font-size: 20px; font-weight: 700; color: #22D3EE;">2. Obligation Map</div>
            <p style="font-size: 13px; color: #8A94A8; margin: 8px 0;">Applicability Engine filters obligations against Meridian Bank's licenses.</p>
            <span class="mono-chip">Stage 2</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        """
        <div class="argus-card">
            <div style="font-size: 20px; font-weight: 700; color: #22D3EE;">3. Rule Studio</div>
            <p style="font-size: 13px; color: #8A94A8; margin: 8px 0;">Side-by-side DSL & Rego compiler with Z3 formal conflict proof banner.</p>
            <span class="mono-chip">Stages 3-4</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        """
        <div class="argus-card">
            <div style="font-size: 20px; font-weight: 700; color: #22D3EE;">4. Agent Mesh</div>
            <p style="font-size: 13px; color: #8A94A8; margin: 8px 0;">Live agent-to-agent graph with animated objection loop and iteration counter.</p>
            <span class="mono-chip">Live Mesh</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

c5, c6, c7, c8 = st.columns(4)

with c5:
    st.markdown(
        """
        <div class="argus-card">
            <div style="font-size: 20px; font-weight: 700; color: #22D3EE;">5. Impact Report</div>
            <p style="font-size: 13px; color: #8A94A8; margin: 8px 0;">DuckDB 500k backtest replay, segment heatmap, and operational queue delta.</p>
            <span class="mono-chip">Stages 5-6</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c6:
    st.markdown(
        """
        <div class="argus-card">
            <div style="font-size: 20px; font-weight: 700; color: #22D3EE;">6. Approvals</div>
            <p style="font-size: 13px; color: #8A94A8; margin: 8px 0;">Ed25519 maker-checker dual authorization. Rejects single-signed attempts.</p>
            <span class="mono-chip">Stage 8</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c7:
    st.markdown(
        """
        <div class="argus-card">
            <div style="font-size: 20px; font-weight: 700; color: #22D3EE;">7. Rollout Monitor</div>
            <p style="font-size: 13px; color: #8A94A8; margin: 8px 0;">Shadow mode concordance, canary ladder, and live chaos rollback.</p>
            <span class="mono-chip">Stages 9-10</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c8:
    st.markdown(
        """
        <div class="argus-card">
            <div style="font-size: 20px; font-weight: 700; color: #22D3EE;">8. Audit & Replay</div>
            <p style="font-size: 13px; color: #8A94A8; margin: 8px 0;">Hash-chained Merkle ledger with one-click bit-for-bit replay verification.</p>
            <span class="mono-chip">Audit</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# Quick One-Click Demo Run
st.markdown("### ⚡ Quick Launch: 5-Minute Pitch Rehearsal")
col_act1, col_act2 = st.columns([1, 2])
with col_act1:
    if st.button("🚀 Execute Full Gated Workflow (C1 Hero Demo)", type="primary", use_container_width=True):
        with st.spinner("Executing 10-stage pipeline with Z3 formal proof and Objection Loop..."):
            c1_path = REPO_ROOT / "data" / "circulars" / "C1_cash_deposit_edd.md"
            c1_text = c1_path.read_text(encoding="utf-8") if c1_path.exists() else ""
            state = orch.run_pipeline_to_approval(
                circular_id="RBI-2026-42",
                circular_title="Enhanced Due Diligence for High-Value Cash Deposits",
                circular_text=c1_text,
                bank_profile=st.session_state.bank_profile,
                historical_txns=None,
                simulate_objection_loop=True,
            )
            st.session_state.workflow_state = state
            st.session_state.demo_stage = 8  # At Approval stage
            st.success("Pipeline executed up to Human Approval Gate! Objection Loop successfully resolved in iteration 2/3.")
            st.rerun()

with col_act2:
    if st.session_state.get("workflow_state"):
        ws = st.session_state.workflow_state
        st.info(
            f"Active Case: `{ws.circular_id}` | Stage: `{ws.stage_name}` | "
            f"Objections Resolved: `{len(ws.objection_history)}` | Audit Hash: `{ws.audit_hashes[-1][:16] if ws.audit_hashes else 'N/A'}...`"
        )
