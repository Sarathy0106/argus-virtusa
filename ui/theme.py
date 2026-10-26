"""
ARGUS v2 UI Styling and Theme Module.
Provides cyber-compliance dark glassmorphism styling, custom typography,
interactive stage badges, telemetry metric cards, and responsive components.
"""

import streamlit as st


def inject_custom_css():
    st.markdown(
        """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre, [class*="stCode"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Top Brand Bar */
    .brand-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.6) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.2rem 1.8rem;
        margin-bottom: 1.8rem;
        backdrop-filter: blur(16px);
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }

    .brand-title-box {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .brand-logo {
        font-size: 2.2rem;
        filter: drop-shadow(0 0 16px rgba(6, 182, 212, 0.6));
    }

    .brand-title {
        font-size: 1.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FFFFFF 0%, #E2E8F0 50%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }

    .brand-tagline {
        font-size: 0.85rem;
        color: #94A3B8;
        font-weight: 500;
        margin-top: 0.15rem;
    }

    .brand-badges {
        display: flex;
        gap: 0.6rem;
        align-items: center;
    }

    /* Pill Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.35rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        border: 1px solid transparent;
    }

    .badge-cyan {
        background: rgba(6, 182, 212, 0.15);
        color: #38BDF8;
        border-color: rgba(6, 182, 212, 0.3);
    }

    .badge-green {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border-color: rgba(16, 185, 129, 0.3);
    }

    .badge-amber {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border-color: rgba(245, 158, 11, 0.3);
    }

    .badge-red {
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border-color: rgba(239, 68, 68, 0.3);
    }

    .badge-purple {
        background: rgba(139, 92, 246, 0.15);
        color: #A78BFA;
        border-color: rgba(139, 92, 246, 0.3);
    }

    /* Glass Cards */
    .glass-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 1.4rem;
        margin-bottom: 1.2rem;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .glass-card:hover {
        border-color: rgba(56, 189, 248, 0.25);
    }

    .glass-card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* KPI Metrics Grid */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 1.8rem;
    }

    .kpi-card {
        background: linear-gradient(145deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.5) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(10px);
        transition: all 0.25s ease;
    }

    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px -6px rgba(6, 182, 212, 0.25);
        border-color: rgba(6, 182, 212, 0.4);
    }

    .kpi-value {
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        line-height: 1.1;
    }

    .kpi-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-top: 0.4rem;
    }

    .kpi-sub {
        font-size: 0.75rem;
        color: #64748B;
        margin-top: 0.3rem;
    }

    /* 10-Stage Pipeline Stepper Bar */
    .stepper-container {
        display: flex;
        align-items: center;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 0.8rem 1rem;
        margin-bottom: 1.8rem;
        overflow-x: auto;
        gap: 0.4rem;
    }

    .step-node {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.45rem 0.8rem;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 600;
        white-space: nowrap;
        background: rgba(30, 41, 59, 0.5);
        color: #94A3B8;
        border: 1px solid rgba(255, 255, 255, 0.05);
        transition: all 0.2s ease;
    }

    .step-active {
        background: linear-gradient(135deg, rgba(6, 182, 212, 0.2) 0%, rgba(59, 130, 246, 0.2) 100%);
        color: #38BDF8;
        border-color: rgba(56, 189, 248, 0.5);
        box-shadow: 0 0 12px rgba(6, 182, 212, 0.25);
    }

    .step-completed {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border-color: rgba(52, 211, 153, 0.4);
    }

    .step-arrow {
        color: #475569;
        font-size: 0.75rem;
    }

    /* Streamlit Tabs Customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(15, 23, 42, 0.7);
        padding: 0.4rem 0.5rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .stTabs [data-baseweb="tab"] {
        height: 2.8rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.88rem;
        color: #94A3B8;
        padding: 0 1.2rem;
        background: transparent;
        border: none;
        transition: all 0.2s ease;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #06B6D4 0%, #3B82F6 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 14px rgba(6, 182, 212, 0.35);
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 0.01em;
        transition: all 0.2s ease;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #06B6D4 0%, #3B82F6 100%);
        border: none;
        box-shadow: 0 4px 14px rgba(6, 182, 212, 0.35);
    }

    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(6, 182, 212, 0.5);
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.6) !important;
        border-radius: 8px !important;
        font-weight: 600;
        color: #F1F5F9 !important;
    }
</style>
""",
        unsafe_allow_html=True,
    )


def render_brand_header(current_stage_num: int = 1, current_stage_name: str = "CIRCULAR_INTAKE"):
    st.markdown(
        f"""
<div class="brand-header">
    <div class="brand-title-box">
        <div class="brand-logo">🛡️</div>
        <div>
            <div class="brand-title">ARGUS v2 <span style="font-size: 0.95rem; font-weight: 600; color: #38BDF8; margin-left: 0.4rem;">FDS NA USE CASE 2</span></div>
            <div class="brand-tagline">Autonomous Regulatory Guard with Unified Safety — Circular to Live Rule Engine</div>
        </div>
    </div>
    <div class="brand-badges">
        <div class="badge badge-green">● PII AIRLOCK: ZERO LEAKS</div>
        <div class="badge badge-cyan">● STAGE {current_stage_num}/10: {current_stage_name}</div>
        <div class="badge badge-purple">● ED25519 MESH: SIGNED</div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_pipeline_stepper(active_stage: int = 1):
    stages = [
        ("1", "Intake"),
        ("2", "Obligation"),
        ("3", "Mapping"),
        ("4", "Rule DSL"),
        ("5", "Backtest"),
        ("6", "Impact"),
        ("7", "Validation"),
        ("8", "Approval"),
        ("9", "Shadow"),
        ("10", "Rollout"),
    ]

    nodes_html = []
    for num_str, name in stages:
        num = int(num_str)
        if num == active_stage:
            cls = "step-node step-active"
            icon = "⚡"
        elif num < active_stage:
            cls = "step-node step-completed"
            icon = "✔"
        else:
            cls = "step-node"
            icon = f"{num}."
        nodes_html.append(f'<div class="{cls}"><span>{icon}</span> {name}</div>')

    stepper_html = f'<div class="stepper-container">{" <span class=\"step-arrow\">➔</span> ".join(nodes_html)}</div>'
    st.markdown(stepper_html, unsafe_allow_html=True)
