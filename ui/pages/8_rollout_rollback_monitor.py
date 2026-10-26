"""
Page 8: Rollout Monitor, Shadow Deployment & Automatic Rollback (Stages 9 & 10).
Controls shadow parallel evaluation, progressive canary ramp (1% -> 100%),
drift telemetry tracking, and sub-second automatic rollback on threshold breaches.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import streamlit as st
from contracts.deployment import DeploymentStage
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator
from ui.theme import inject_custom_css, render_brand_header, render_pipeline_stepper

st.set_page_config(page_title="Rollout & Rollback Monitor | ARGUS v2", page_icon="📡", layout="wide")
inject_custom_css()
render_brand_header(current_stage_num=10, current_stage_name="ROLLOUT_AND_MONITORING")
render_pipeline_stepper(active_stage=10)


if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

# Ensure approved workflow state exists
if "workflow_state" not in st.session_state or not st.session_state.workflow_state or not st.session_state.workflow_state.approval_token:
    SAMPLE_CIRCULAR = """
Reserve Bank of India
Notification: RBI/2024-25/118
Section 2: High-Value Immediate Transfer Cooling Period
All regulated entities shall enforce a mandatory cooling period of 4 hours for any retail immediate payment
or UPI transaction where the single transaction amount meets or exceeds INR 50,000.
"""
    state = orch.run_pipeline_to_approval(
        circular_id="RBI-2024-118",
        circular_title="UPI Risk Management",
        circular_text=SAMPLE_CIRCULAR,
        bank_profile=st.session_state.bank_profile,
        historical_txns=st.session_state.historical_txns,
    )
    orch.grant_dual_approval(state, maker_id="analyst_rajesh", checker_id="officer_priya")
    st.session_state.workflow_state = state

state = st.session_state.workflow_state

# Active version banner
curr_ver = orch.deployment_agent.active_bundle_version
prev_ver = orch.deployment_agent.previous_bundle_version
deploy_stage = orch.deployment_agent.deployment_stage.value

b1, b2, b3 = st.columns(3)
b1.metric("Active Rule Bundle", f"v{curr_ver}")
b2.metric("Previous Stable Release", f"v{prev_ver}")
b3.metric("Deployment Lifecycle Stage", deploy_stage)

st.divider()

# Controls
st.subheader("Rollout & Telemetry Controls")
c_opt, c_run = st.columns([1.2, 0.8])
with c_opt:
    sim_breach = st.checkbox("Trigger Simulated Safety Drift Breach at 50% Canary (Decline Rate > 5%, Latency > 50ms)", value=True)

with c_run:
    if st.button("🚀 Execute Shadow Evaluation & Canary Ramp", type="primary"):
        with st.spinner("Evaluating live shadow stream and ramping canary stages..."):
            state = orch.execute_shadow_and_rollout(
                state=state,
                live_transactions=st.session_state.historical_txns,
                force_canary_breach=sim_breach,
            )
            st.session_state.workflow_state = state
        st.success("Shadow evaluation and canary monitoring completed!")

if state.shadow_evaluation:
    st.divider()
    st.subheader("Stage 9: Shadow Parallel Evaluation Results")
    se = state.shadow_evaluation

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Live Traffic Evaluated", se.total_evaluations)
    s2.metric("Concordance with Live Rules", f"{se.concordance_percentage}%")
    s3.metric("Backtest Drift", f"{se.drift_from_backtest_pct}%", delta="Within Safe Tolerance" if se.within_tolerance else "High Drift")
    s4.metric("Shadow Alerts Logged", se.shadow_rule_alerts)

if state.canary_metrics:
    st.divider()
    st.subheader("Stage 10: Canary Stream Telemetry (1% ➔ 10% ➔ 50% ➔ 100%)")

    metric_rows = []
    for cm in state.canary_metrics:
        metric_rows.append(
            {
                "Stage": cm.stage.value,
                "Traffic (%)": f"{cm.traffic_pct}%",
                "Evaluations": cm.evaluations_count,
                "Alert Rate (%)": f"{cm.alert_rate_pct}%",
                "Decline Rate (%)": f"{cm.decline_rate_pct}%",
                "p95 Latency": f"{cm.latency_p95_ms:.1f} ms",
                "Breach Detected": "🚨 YES" if cm.breach_detected else "✅ Normal",
            }
        )
    st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)

    # Telemetry Chart
    df_chart = pd.DataFrame(
        {
            "Stage": [m["Stage"] for m in metric_rows],
            "Decline Rate (%)": [float(m["Decline Rate (%)"].replace("%", "")) for m in metric_rows],
            "Latency (ms)": [float(m["p95 Latency"].replace(" ms", "")) for m in metric_rows],
        }
    ).set_index("Stage")
    st.line_chart(df_chart)

if state.rollback_record:
    st.divider()
    rb = state.rollback_record
    st.error(
        f"""
### 🚨 AUTOMATIC ROLLBACK TRIGGERED (< 1.0 Second Recovery)
- **Rollback Incident ID:** `{rb.rollback_id}`
- **Triggered By:** `{rb.triggered_by}`
- **Reason:** `{rb.reason}`
- **Bundle Pointer Reversion:** `v{rb.from_version}` ➔ `v{rb.to_version}`
- **Recovery Time:** `{rb.recovery_time_ms:.2f} milliseconds`
"""
    )
    st.success("✅ Atomic pointer restored. System is safely operating on previous stable bundle without downtime.")
