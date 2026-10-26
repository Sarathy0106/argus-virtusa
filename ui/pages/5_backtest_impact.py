"""
Page 5: Backtesting & Operational Impact Report (Stages 5 & 6).
Replays historical transactions through sandbox policy engine to compute
alert/decline deltas, affected customer segments, and ops queue surges.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import streamlit as st
from services.ingest.simulator import SyntheticTransactionGenerator
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator
from ui.theme import inject_custom_css, render_brand_header, render_pipeline_stepper

st.set_page_config(page_title="Backtest & Impact | ARGUS v2", page_icon="📊", layout="wide")
inject_custom_css()
render_brand_header(current_stage_num=5, current_stage_name="BACKTESTING_AND_IMPACT")
render_pipeline_stepper(active_stage=5)


if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

if "historical_txns" not in st.session_state:
    gen = SyntheticTransactionGenerator(seed=42)
    st.session_state.historical_txns = gen.generate_dataset(250)

# Ensure rule definition exists
if "rule_definition" not in st.session_state:
    SAMPLE_CIRCULAR = """
Reserve Bank of India
Notification: RBI/2024-25/118
Section 2: High-Value Immediate Transfer Cooling Period
All regulated entities shall enforce a mandatory cooling period of 4 hours for any retail immediate payment
or UPI transaction where the single transaction amount meets or exceeds INR 50,000.
"""
    intake = orch.intake_agent.process_circular("RBI-2024-118", "UPI Risk Management", SAMPLE_CIRCULAR)
    obls = orch.obligation_agent.extract_obligations(intake["clauses"], st.session_state.bank_profile)
    mapping = orch.policy_mapper_agent.map_obligations(obls, bank_id=st.session_state.bank_profile.bank_id)
    r_def, rego, tests = orch.rule_author_agent.author_rule(obls[0], mapping.mappings[0], iteration=2)
    st.session_state.rule_definition = r_def

txns = st.session_state.historical_txns
r_def = st.session_state.rule_definition

col1, col2 = st.columns([1.2, 0.8])
with col1:
    st.info(f"**Target Rule:** `{r_def.rule_name}` (v{r_def.version}) | **Dataset:** `{len(txns)} Historical Transactions`")

with col2:
    if st.button("🚀 Run Sandboxed Backtest & Impact Analysis", type="primary"):
        with st.spinner("Replaying historical transaction stream in isolated sandbox..."):
            bt = orch.backtest_agent.run_backtest(r_def, txns)
            imp = orch.impact_agent.analyze_impact(bt)
            st.session_state.backtest_result = bt
            st.session_state.impact_report = imp
        st.success(f"Backtesting completed in {bt.avg_latency_ms * len(txns):.1f} ms!")

if "backtest_result" in st.session_state:
    bt = st.session_state.backtest_result
    imp = st.session_state.impact_report
    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Baseline Alerts", bt.baseline_alerts)
    m2.metric("Candidate Alerts", bt.candidate_alerts, delta=f"+{bt.delta_alerts}")
    m3.metric("Flagged Volume", f"₹{bt.total_flagged_volume:,.0f}")
    m4.metric("Estimated Ops Load", f"~{imp.estimated_ops_hours_per_day} hrs/day")

    col_chart, col_seg = st.columns([1, 1])

    with col_chart:
        st.subheader("Alert Volume Comparison")
        chart_data = pd.DataFrame(
            {
                "Engine Version": ["Baseline Rules", "Candidate Draft Rule"],
                "Alert Count": [bt.baseline_alerts, bt.candidate_alerts],
            }
        ).set_index("Engine Version")
        st.bar_chart(chart_data)

    with col_seg:
        st.subheader("Affected Customer Segments")
        seg_rows = []
        for s in imp.segments:
            seg_rows.append(
                {
                    "Segment": s.segment_name,
                    "Accounts Impacted": s.impacted_accounts,
                    "Flagged Volume (INR)": f"₹{s.volume_flagged_inr:,.0f}",
                    "Share (%)": f"{s.share_of_alerts_pct}%",
                }
            )
        st.dataframe(pd.DataFrame(seg_rows), use_container_width=True, hide_index=True)

    st.subheader("Operational Risk Assessment")
    if imp.risk_verdict == "SAFE":
        st.success("🟢 **Risk Verdict: SAFE** — Alert volume surge and false-positive rates are well within operational capacity limits.")
    elif imp.risk_verdict == "ELEVATED":
        st.warning("🟡 **Risk Verdict: ELEVATED** — Noticeable queue load increase. Review analyst staffing prior to promotion.")
    else:
        st.error(f"🔴 **Risk Verdict: EXCESSIVE SURGE** — {imp.objection.message if imp.objection else 'Surge exceeds tolerance'}")
