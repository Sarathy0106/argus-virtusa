"""
ARGUS v2 — Stages 5 & 6: Sandbox Backtesting & Impact Analysis
Backtest Agent & Impact Agent: Evaluates candidate rule changes over historical transaction data,
calculates alert volume delta, customer segment shifts, and operations load estimates.
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
import plotly.graph_objects as go
import plotly.express as px

from ui.components import (
    inject_css, page_header, section_header, render_kpi_row,
    render_ten_stage_pipeline, render_bank_profile_header,
    verified_banner, warning_banner, badge
)
from ui.services.client_v2 import get_sample_pipeline


st.set_page_config(page_title="Backtest & Impact — ARGUS v2", page_icon="📊", layout="wide")
inject_css()

page_header(
    "📊 Stages 5 & 6: Sandbox Backtest & Operational Impact",
    "Backtest Agent & Impact Agent · Historical replay sandbox · Volume delta · Segment shifts · Operations workload"
)
render_ten_stage_pipeline(active_stage=5)
st.markdown("---")
render_bank_profile_header()

case = get_sample_pipeline()
bt = case["backtest_report"]

with st.sidebar:
    st.markdown("### 📊 Stages 5 & 6: Sandbox & Impact")
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.8rem;color:#94A3B8;'>"
        "Executes candidate rule against historical transactions (PaySim / bank replay corpus) "
        "in an isolated OPA sandbox. Quantifies false-positive expansion and analyst ops load "
        "before reaching compliance reviewers.</div>",
        unsafe_allow_html=True,
    )

# KPI Row
render_kpi_row([
    {"label": "Transactions Tested",    "value": f"{bt['total_transactions_analyzed']:,}", "sub": "historical sandbox"},
    {"label": "Baseline Alerts (v1.0)", "value": str(bt["baseline_alert_count"]),           "sub": "existing rule"},
    {"label": "Candidate Alerts",       "value": str(bt["candidate_alert_count"]),          "sub": "proposed rule", "color": "amber"},
    {"label": "Alert Volume Δ",         "value": f"+{bt['delta_percentage']:.1f}%",        "sub": "+16 monthly alerts", "color": "red"},
    {"label": "Total Flagged Volume",   "value": f"₹{bt['total_flagged_volume_inr']/1000000:.2f}M", "sub": "INR cumulative", "color": "blue"},
])

st.markdown("<div style='height:1.25rem;'></div>", unsafe_allow_html=True)

col_chart, col_ops = st.columns([1, 1])

with col_chart:
    section_header("Affected Customer Segments")
    seg_data = bt["affected_customer_segments"]
    labels = [s["segment"] for s in seg_data]
    vals = [s["share_pct"] for s in seg_data]
    
    fig_pie = go.Figure(go.Pie(
        labels=labels,
        values=vals,
        hole=0.45,
        marker=dict(colors=["#3B82F6", "#10B981", "#F59E0B"]),
        textinfo="label+percent",
    ))
    fig_pie.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="#111827",
        font=dict(color="#F8FAFC", family="Plus Jakarta Sans"),
        legend=dict(orientation="h", y=-0.15, font=dict(color="#CBD5E1")),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_ops:
    section_header("Operational Workload & False-Positive Forecast")
    st.markdown(
        f"<div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1.25rem;'>"
        f"<div style='display:flex;justify-content:space-between;border-bottom:1px solid #1E293B;padding-bottom:0.75rem;'>"
        f"<div><span style='color:#94A3B8;font-size:0.75rem;'>ESTIMATED OPS OVERHEAD</span><br><b style='font-size:1.3rem;color:#FCD34D;'>+{bt['estimated_ops_hours_per_month']} hrs/mo</b></div>"
        f"<div><span style='color:#94A3B8;font-size:0.75rem;'>FALSE POSITIVE RATE</span><br><b style='font-size:1.3rem;color:#34D399;'>{bt['false_positive_estimate_pct']}%</b></div>"
        f"<div><span style='color:#94A3B8;font-size:0.75rem;'>SANDBOX RUN ID</span><br><code style='color:#60A5FA;font-size:0.85rem;'>{bt['sandbox_run_id']}</code></div>"
        f"</div>"
        f"<div style='margin-top:0.85rem;color:#CBD5E1;font-size:0.85rem;line-height:1.6;'>"
        f"• <b>Primary Impact:</b> Corporate trade remittance desks will see an increase from 12 to 28 alerts/month.<br>"
        f"• <b>Capacity Assessment:</b> Operations desk possesses surplus capacity (+24 hrs available), absorbing the +14.5 hr delta without staffing expansion.<br>"
        f"• <b>Compliance Verdict:</b> Alert volume delta is proportional to statutory closure of the ₹200,000 regulatory gap."
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
    verified_banner("Impact Analysis Complete — Backtest results archived into Sandbox Ledger")

st.markdown("---")
col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("← Back to Stage 4: Rule Authoring"):
        st.switch_page("pages/4_rule_studio.py")
with col_nav2:
    st.markdown("<div style='display:flex;justify-content:flex-end;'>", unsafe_allow_html=True)
    if st.button("Proceed to Stage 7: Validation Gate →", type="primary"):
        st.switch_page("pages/6_validator_objection_loop.py")
    st.markdown("</div>", unsafe_allow_html=True)
