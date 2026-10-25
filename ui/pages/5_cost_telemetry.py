"""
Page 5: Cost Router & Telemetry Dashboard.
"""

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

st.set_page_config(page_title="Cost & Telemetry | ARGUS", page_icon="📈", layout="wide")

st.title("📈 Cost Router & Telemetry Dashboard")
st.caption("Monitoring tiered execution cascades, token budget ceilings, and latency benchmarks.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Decisions Routed via Rules / ML", "84%", delta="84% Zero-Token Path")
with col2:
    st.metric("Semantic Cache Hit Ratio", "38.2%", delta="+5.1%")
with col3:
    st.metric("Avg T0 Latency", "32 ms", delta="-12 ms vs target")
with col4:
    st.metric("Estimated Cost Savings vs Cloud API", "$2,450 / mo", delta="98.5% savings")

st.subheader("1. Tiered Execution Cascade")
st.caption(
    "Transactions cascade through the cheapest sufficient tier. LLMs are only invoked for ambiguous narrative drafting."
)

cascade_data = [
    {
        "Tier": "1. Semantic Cache",
        "Latency": "< 2 ms",
        "Token Cost": "0 tokens",
        "Inference Cost": "$0.00",
        "Volume": "38%",
    },
    {
        "Tier": "2. OPA Policy Engine",
        "Latency": "< 5 ms",
        "Token Cost": "0 tokens",
        "Inference Cost": "$0.00",
        "Volume": "46%",
    },
    {
        "Tier": "3. Calibrated LightGBM Scorer",
        "Latency": "< 25 ms",
        "Token Cost": "0 tokens",
        "Inference Cost": "$0.00",
        "Volume": "11%",
    },
    {
        "Tier": "4. Local LLM (Ollama)",
        "Latency": "~ 1.8 s",
        "Token Cost": "~ 350 tokens",
        "Inference Cost": "$0.00 (Local Hardware)",
        "Volume": "5%",
    },
]
st.table(cascade_data)

st.subheader("2. Per-Customer Daily Token Budgets")
st.caption("Guards against denial-of-wallet attacks and abusive prompt loops.")

col_u1, col_u2 = st.columns(2)
with col_u1:
    st.write("**Customer: `<ACCT_CORP_4B9A>`** (Ceiling: 15,000 tokens/day)")
    st.progress(0.35, text="5,250 / 15,000 tokens consumed (35%)")
with col_u2:
    st.write("**Customer: `<ACCT_RETAIL_1201>`** (Ceiling: 5,000 tokens/day)")
    st.progress(0.12, text="600 / 5,000 tokens consumed (12%)")

st.subheader("3. Latency Distribution Percentiles")
c_p50, c_p95, c_p99 = st.columns(3)
with c_p50:
    st.metric("p50 Decision Latency", "24 ms")
with c_p95:
    st.metric("p95 Decision Latency", "48 ms")
with c_p99:
    st.metric("p99 Decision Latency (with LLM Narrative)", "2.1 s")
