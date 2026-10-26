"""
ARGUS v2 — Stages 9 & 10: Shadow Deployment, Canary Rollout & Automatic Rollback
Deployment Agent & Monitor Agent: Manages non-enforcing parallel shadow evaluation,
canary traffic ramps (1% -> 10% -> 50% -> 100%), and automatic rollback on metric breach.
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

from datetime import datetime, timezone
import random
import streamlit as st
import plotly.graph_objects as go

from ui.components import (
    inject_css, page_header, section_header, render_kpi_row,
    render_ten_stage_pipeline, render_bank_profile_header,
    verified_banner, warning_banner, badge
)
from ui.services.client_v2 import get_sample_pipeline, trigger_instant_rollback


st.set_page_config(page_title="Rollout & Rollback — ARGUS v2", page_icon="🚀", layout="wide")
inject_css()

page_header(
    "🚀 Stages 9 & 10: Shadow Deployment, Canary & Automatic Rollback",
    "Deployment Agent & Monitor Agent · Non-enforcing shadow evaluation · Canary ramp · Anomaly detection · Instant Git rollback"
)
render_ten_stage_pipeline(active_stage=9)
st.markdown("---")
render_bank_profile_header()

case = get_sample_pipeline()
rollout = case["rollout"]

with st.sidebar:
    st.markdown("### 🚀 Stages 9 & 10: Rollout & Rollback")
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.8rem;color:#94A3B8;'>"
        "<b>Shadow-First Architecture:</b> Rules evaluate parallel traffic without enforcement until verified. "
        "<b>Reversible Rollout:</b> Every release is a Git-tagged bundle. If impact or latency breaches threshold, "
        "the Monitor Agent executes a 1-step pointer rollback in &lt;1 second.</div>",
        unsafe_allow_html=True,
    )

# Rollback State Tracking
if "v2_is_rolled_back" not in st.session_state:
    st.session_state["v2_is_rolled_back"] = False
if "v2_canary_pct" not in st.session_state:
    st.session_state["v2_canary_pct"] = 10

is_rolled_back = st.session_state["v2_is_rolled_back"]
canary_pct = st.session_state["v2_canary_pct"]

# Rollback Alert if triggered
if is_rolled_back:
    st.markdown(
        "<div style='background:rgba(239,68,68,0.15);border:2px solid #EF4444;border-radius:10px;padding:1.25rem;margin-bottom:1.25rem;'>"
        "<div style='display:flex;align-items:center;gap:0.75rem;'>"
        "<span style='font-size:2rem;'>🚨</span>"
        "<div>"
        "<div style='font-size:1.15rem;font-weight:800;color:#FCA5A5;'>AUTOMATIC ROLLBACK EXECUTED (Latency: 480ms)</div>"
        "<div style='color:#F8FAFC;font-size:0.88rem;margin-top:0.2rem;'>"
        "Monitor Agent detected live traffic divergence breach (14.8% &gt; 5.0% threshold). "
        "Rule bundle reverted from <code>v1.1.0-canary</code> back to stable tag <code>v1.0.0</code>. Zero unauthorized enforcement occurred."
        "</div>"
        "</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("🔄 Reset Live Deployment (Re-engage Canary Ramp)"):
        st.session_state["v2_is_rolled_back"] = False
        st.session_state["v2_canary_pct"] = 10
        st.rerun()

# KPI Row
current_tag = "v1.0.0 (Rolled Back)" if is_rolled_back else f"v1.1.0 (Canary {canary_pct}%)"
current_state = "ROLLED_BACK" if is_rolled_back else f"CANARY_{canary_pct}%"

render_kpi_row([
    {"label": "Active Bundle Tag",      "value": current_tag,                       "sub": "Git-tagged policy bundle", "color": "red" if is_rolled_back else "blue"},
    {"label": "Canary Traffic Share",  "value": f"{0 if is_rolled_back else canary_pct}%", "sub": "active live routing", "color": "amber" if not is_rolled_back else "red"},
    {"label": "Shadow Stream Events",  "value": f"{rollout['shadow_events_count']:,}", "sub": "parallel non-enforcing"},
    {"label": "Divergence Rate",       "value": f"{14.8 if is_rolled_back else rollout['divergence_rate_pct']}%", "sub": "threshold: 5.0% max", "color": "red" if is_rolled_back else "green"},
    {"label": "Evaluation Latency P95","value": f"{rollout['p95_eval_latency_ms']} ms",  "sub": "target: <10ms", "color": "green"},
])

st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

tab_canary, tab_shadow, tab_architecture = st.tabs([
    "📈 Stage 10: Canary Rollout & Auto-Rollback",
    "👥 Stage 9: Shadow Evaluation Stream",
    "🏛️ Reversible Deployment Architecture"
])

with tab_canary:
    section_header("Canary Traffic Controller")
    
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        st.markdown("**Progressive Canary Allocation**")
        selected_ramp = st.select_slider(
            "Select Canary Traffic Percentage",
            options=[1, 10, 25, 50, 100],
            value=canary_pct,
            disabled=is_rolled_back,
            key="canary_slider_select"
        )
        if selected_ramp != canary_pct and not is_rolled_back:
            st.session_state["v2_canary_pct"] = selected_ramp
            st.rerun()
        st.markdown(f"Current live allocation: **{selected_ramp}% of outward corporate wire transactions** routed to candidate rule.")

    with col_c2:
        st.markdown("**Emergency Anomaly Simulation**")
        if not is_rolled_back:
            if st.button("⚡ Simulate Metric Breach & Trigger Auto-Rollback", type="primary", key="btn_trigger_rollback"):
                st.session_state["v2_is_rolled_back"] = True
                st.rerun()
            st.markdown("<span style='font-size:0.75rem;color:#94A3B8;'>Forces a simulated 14.8% divergence spike to demonstrate automatic sub-second rollback.</span>", unsafe_allow_html=True)

    # Live Drift Monitor Chart
    section_header("Live Divergence & Anomaly Monitoring Stream (Last 60 Minutes)")
    
    rng = random.Random(42)
    minutes = list(range(1, 61))
    if is_rolled_back:
        div_points = [rng.uniform(0.2, 0.6) for _ in range(50)] + [rng.uniform(6.0, 15.2) for _ in range(10)]
    else:
        div_points = [rng.uniform(0.2, 0.7) for _ in minutes]

    fig_mon = go.Figure()
    fig_mon.add_trace(go.Scatter(
        x=minutes, y=div_points, mode="lines",
        name="Candidate Divergence %",
        line=dict(color="#EF4444" if is_rolled_back else "#3B82F6", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(239,68,68,0.15)" if is_rolled_back else "rgba(59,130,246,0.1)",
    ))
    fig_mon.add_hline(
        y=5.0, line_dash="dash", line_color="#EF4444",
        annotation_text="Auto-Rollback Threshold (5.0%)", annotation_position="top left",
        annotation_font_color="#FCA5A5"
    )
    fig_mon.update_layout(
        height=280,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="#111827", plot_bgcolor="#111827",
        font=dict(color="#CBD5E1", family="Plus Jakarta Sans"),
        xaxis=dict(title="Minutes Ago (Rolling Window)", gridcolor="#1E293B"),
        yaxis=dict(title="Divergence Rate (%)", gridcolor="#1E293B"),
    )
    st.plotly_chart(fig_mon, use_container_width=True)

with tab_shadow:
    section_header("Parallel Shadow Evaluation Stream")
    st.markdown(
        f"<div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1.25rem;'>"
        f"<div style='color:#34D399;font-weight:700;font-size:0.95rem;'>SHADOW EVALUATION AUDIT PASSED</div>"
        f"<div style='color:#CBD5E1;font-size:0.88rem;margin-top:0.4rem;line-height:1.6;'>"
        f"• <b>Live Traffic Processed:</b> {rollout['shadow_events_count']:,} transactions evaluated in parallel.<br>"
        f"• <b>Enforcement Status:</b> PASS-THROUGH ONLY (Candidate decisions logged but not enforced on core banking core).<br>"
        f"• <b>Behavioral Match:</b> Shadow divergence of 0.37% confirms candidate matches sandbox backtest within target ±1.0% tolerance."
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

with tab_architecture:
    section_header("One-Step Git-Tagged Bundle Rollback Architecture")
    st.markdown(
        "<div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1.25rem;color:#CBD5E1;font-size:0.88rem;line-height:1.7;'>"
        "1. <b>Immutable Packaging:</b> Every approved rule change is committed to the Git rule repository as a signed tag (e.g. <code>v1.1.0-canary</code>).<br>"
        "2. <b>Stateless OPA Sidecars:</b> Production rule engines mount policies via symlinked bundle pointers.<br>"
        "3. <b>Sub-Second Rollback:</b> When the Monitor Agent or human operator triggers a rollback, the Deployment API updates the symlink pointer back to <code>v1.0.0</code> and issues an in-memory SIGHUP reload. Total elapsed time: <b>480 milliseconds</b>.<br>"
        "4. <b>Audit Attestation:</b> Emergency rollback events are cryptographically recorded into the SHA-256 Merkle ledger."
        "</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")
col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("← Back to Stage 8: Human Approval"):
        st.switch_page("pages/7_governance_approvals.py")
with col_nav2:
    st.markdown("<div style='display:flex;justify-content:flex-end;'>", unsafe_allow_html=True)
    if st.button("View Audit Ledger & Replay Explorer →", type="primary"):
        st.switch_page("pages/9_audit_explorer.py")
    st.markdown("</div>", unsafe_allow_html=True)
