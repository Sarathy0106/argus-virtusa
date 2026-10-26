"""
ARGUS v2 — Circular to Live Rule Engine Dashboard
Master console orchestrating the 10-stage regulatory pipeline for FDS NA Use Case 2.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UI_ROOT = Path(__file__).resolve().parent

if str(UI_ROOT) in sys.path:
    sys.path.remove(str(UI_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
elif sys.path[0] != str(REPO_ROOT):
    sys.path.remove(str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

st.set_page_config(
    page_title="ARGUS v2 — Circular to Live Rule Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    from ui.components import (
        inject_css, render_bank_profile_header, render_ten_stage_pipeline,
        page_header, render_kpi_row, status_pill,
    )
    from ui.services.client_v2 import (
        get_active_bank_profile, get_all_circulars, get_sample_pipeline_case
    )
except ModuleNotFoundError:
    from components import (
        inject_css, render_bank_profile_header, render_ten_stage_pipeline,
        page_header, render_kpi_row, status_pill,
    )
    from services.client_v2 import (
        get_active_bank_profile, get_all_circulars, get_sample_pipeline_case
    )

inject_css()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        "<div style='display:flex;align-items:center;gap:0.6rem;padding:0.25rem 0 0.75rem 0;'>"
        "<span style='font-size:1.6rem;'>🛡️</span>"
        "<div><div style='font-weight:800;font-size:1.15rem;color:#F8FAFC;letter-spacing:-0.02em;'>ARGUS v2</div>"
        "<div style='font-size:0.72rem;color:#3B82F6;font-weight:700;'>CIRCULAR TO LIVE RULE ENGINE</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    
    st.markdown(status_pill(True), unsafe_allow_html=True)
    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
    
    profile = get_active_bank_profile()
    p_name = profile.get("name", "Apex Commercial Bank") if isinstance(profile, dict) else getattr(profile, "bank_name", "Apex Commercial Bank")
    p_type = profile.get("license_type", "COMMERCIAL_BANK") if isinstance(profile, dict) else getattr(profile, "category", "COMMERCIAL_BANK")
    p_tier = profile.get("tier", "TIER_1") if isinstance(profile, dict) else getattr(profile, "tier", "TIER_1")
    p_badge = profile.get("badge", "Scheduled Commercial Bank · AD Cat-1") if isinstance(profile, dict) else getattr(profile, "ad_category", "AD-Cat 1")
    st.markdown(
        f"<div style='background:#111827;border:1px solid #1E293B;border-radius:8px;padding:0.85rem;'>"
        f"<div style='font-size:0.7rem;font-weight:700;color:#94A3B8;text-transform:uppercase;'>Active Bank Profile</div>"
        f"<div style='font-size:0.88rem;font-weight:700;color:#F1F5F9;margin-top:0.2rem;'>{p_name}</div>"
        f"<div style='font-size:0.75rem;color:#60A5FA;margin-top:0.25rem;'>{p_badge}</div>"
        f"<div style='font-size:0.72rem;color:#64748B;margin-top:0.35rem;'>{p_type} · {p_tier}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.75rem;color:#64748B;line-height:1.6;'>"
        "<span style='color:#94A3B8;font-weight:600;'>Architecture:</span> 10-Stage Agentic Pipeline<br>"
        "<span style='color:#94A3B8;font-weight:600;'>Governance:</span> Maker-Checker Dual Control<br>"
        "<span style='color:#94A3B8;font-weight:600;'>Signatures:</span> Ed25519 Cryptographic<br>"
        "<span style='color:#94A3B8;font-weight:600;'>Rule Engine:</span> OPA Rego v1.0.0<br>"
        "<span style='color:#94A3B8;font-weight:600;'>Rollout:</span> Shadow &amp; Canary with Auto-Rollback"
        "</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Bank Profile Banner
# ---------------------------------------------------------------------------
render_bank_profile_header()

# ---------------------------------------------------------------------------
# Page Header
# ---------------------------------------------------------------------------
page_header(
    "🛡️ ARGUS: Regulatory Circular to Live Rule Engine",
    "FDS NA Use Case 2 · 10-Stage Autonomous Compliance-to-Production Pipeline"
)

# ---------------------------------------------------------------------------
# Global Stepper (10 Stages)
# ---------------------------------------------------------------------------
render_ten_stage_pipeline(active_stage=1)

# ---------------------------------------------------------------------------
# Live Metrics Row
# ---------------------------------------------------------------------------
circulars = get_all_circulars()
pipe_case = get_sample_pipeline_case()

render_kpi_row([
    {"label": "Regulatory Circulars", "value": str(len(circulars)), "sub": "Parsed & chunked in vault", "color": "blue"},
    {"label": "Extracted Obligations", "value": "5", "sub": "Clause-level traceability", "color": "blue"},
    {"label": "Active Rule Bundle", "value": "v1.1.0-canary", "sub": "10% Canary live traffic", "color": "green"},
    {"label": "Shadow Engine Discrepancy", "value": "0.00%", "sub": "Zero-defect pass rate", "color": "green"},
    {"label": "Sub-Second Rollback", "value": "480 ms", "sub": "Automated SLO circuit-breaker", "color": "blue"},
])

st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 10-Stage Quick Navigation Hub
# ---------------------------------------------------------------------------
st.markdown("### 🚀 End-to-End Regulatory Pipeline Stages")
st.caption("Select any stage below to inspect its agents, deterministic outputs, and audit proofs.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1.25rem;margin-bottom:1rem;'>
        <div style='display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;'>
            <span style='background:#1E3A8A;color:#60A5FA;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.75rem;font-weight:700;'>STAGES 1 - 3</span>
            <span style='font-size:1rem;font-weight:700;color:#F8FAFC;'>Intake, Applicability & Policy Mapping</span>
        </div>
        <p style='color:#94A3B8;font-size:0.85rem;line-height:1.5;margin:0 0 1rem 0;'>
            Official PDF circular intake via Docling/Marker, metadata extraction, bank-profile applicability engine, and policy gap/conflict detection.
        </p>
        <div style='display:flex;gap:0.5rem;flex-wrap:wrap;'>
            <a href='/circular_inbox' target='_self' style='text-decoration:none;background:#1E293B;color:#F1F5F9;padding:0.4rem 0.8rem;border-radius:6px;font-size:0.8rem;font-weight:600;'>1. Circular Inbox &rarr;</a>
            <a href='/obligation_map' target='_self' style='text-decoration:none;background:#1E293B;color:#F1F5F9;padding:0.4rem 0.8rem;border-radius:6px;font-size:0.8rem;font-weight:600;'>2. Obligation Map &rarr;</a>
            <a href='/policy_mapping' target='_self' style='text-decoration:none;background:#1E293B;color:#F1F5F9;padding:0.4rem 0.8rem;border-radius:6px;font-size:0.8rem;font-weight:600;'>3. Policy Mapping &rarr;</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1.25rem;margin-bottom:1rem;'>
        <div style='display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;'>
            <span style='background:#065F46;color:#34D399;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.75rem;font-weight:700;'>STAGE 4</span>
            <span style='font-size:1rem;font-weight:700;color:#F8FAFC;'>Rule Authoring & Compilation</span>
        </div>
        <p style='color:#94A3B8;font-size:0.85rem;line-height:1.5;margin:0 0 1rem 0;'>
            Deterministic Rule DSL in structured YAML. Compiles directly into Open Policy Agent (OPA) Rego with synthetic unit tests and draft lock.
        </p>
        <div style='display:flex;gap:0.5rem;'>
            <a href='/rule_studio' target='_self' style='text-decoration:none;background:#1E293B;color:#F1F5F9;padding:0.4rem 0.8rem;border-radius:6px;font-size:0.8rem;font-weight:600;'>4. Rule Studio (YAML &amp; OPA) &rarr;</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1.25rem;margin-bottom:1rem;'>
        <div style='display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;'>
            <span style='background:#701A75;color:#E879F9;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.75rem;font-weight:700;'>STAGES 5 - 6</span>
            <span style='font-size:1rem;font-weight:700;color:#F8FAFC;'>Sandbox Backtest & Impact Analysis</span>
        </div>
        <p style='color:#94A3B8;font-size:0.85rem;line-height:1.5;margin:0 0 1rem 0;'>
            Replay candidate rules over 100,000 historical transactions in a strictly isolated sandbox. Quantify volume delta and ops workload.
        </p>
        <div style='display:flex;gap:0.5rem;'>
            <a href='/backtest_impact' target='_self' style='text-decoration:none;background:#1E293B;color:#F1F5F9;padding:0.4rem 0.8rem;border-radius:6px;font-size:0.8rem;font-weight:600;'>5 &amp; 6. Backtest &amp; Impact &rarr;</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1.25rem;margin-bottom:1rem;'>
        <div style='display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;'>
            <span style='background:#831843;color:#F472B6;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.75rem;font-weight:700;'>STAGE 7</span>
            <span style='font-size:1rem;font-weight:700;color:#F8FAFC;'>Validation Gate & Objection Loop</span>
        </div>
        <p style='color:#94A3B8;font-size:0.85rem;line-height:1.5;margin:0 0 1rem 0;'>
            Independent Validator Agent stress-tests candidate rules. Interactive loop: catches policy conflicts, sends rule back for re-authoring.
        </p>
        <div style='display:flex;gap:0.5rem;'>
            <a href='/validator_objection_loop' target='_self' style='text-decoration:none;background:#1E293B;color:#F1F5F9;padding:0.4rem 0.8rem;border-radius:6px;font-size:0.8rem;font-weight:600;'>7. Validator &amp; Objection Loop &rarr;</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1.25rem;margin-bottom:1rem;'>
        <div style='display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;'>
            <span style='background:#78350F;color:#FBBF24;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.75rem;font-weight:700;'>STAGE 8</span>
            <span style='font-size:1rem;font-weight:700;color:#F8FAFC;'>Governance Approvals (Maker-Checker)</span>
        </div>
        <p style='color:#94A3B8;font-size:0.85rem;line-height:1.5;margin:0 0 1rem 0;'>
            Dual-control regulatory governance: Maker cannot approve own rule. Ed25519 digital signatures and signed audit ledger block.
        </p>
        <div style='display:flex;gap:0.5rem;'>
            <a href='/governance_approvals' target='_self' style='text-decoration:none;background:#1E293B;color:#F1F5F9;padding:0.4rem 0.8rem;border-radius:6px;font-size:0.8rem;font-weight:600;'>8. Governance Approvals &rarr;</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1.25rem;margin-bottom:1rem;'>
        <div style='display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;'>
            <span style='background:#14532D;color:#4ADE80;padding:0.2rem 0.6rem;border-radius:6px;font-size:0.75rem;font-weight:700;'>STAGES 9 - 10</span>
            <span style='font-size:1rem;font-weight:700;color:#F8FAFC;'>Shadow, Canary Rollout & Auto-Rollback</span>
        </div>
        <p style='color:#94A3B8;font-size:0.85rem;line-height:1.5;margin:0 0 1rem 0;'>
            Parallel non-enforcing shadow evaluation on live traffic. Canary ramp (1% &rarr; 100%) with drift monitors and 480ms automated rollback.
        </p>
        <div style='display:flex;gap:0.5rem;flex-wrap:wrap;'>
            <a href='/rollout_monitor' target='_self' style='text-decoration:none;background:#1E293B;color:#F1F5F9;padding:0.4rem 0.8rem;border-radius:6px;font-size:0.8rem;font-weight:600;'>8 &amp; 9. Rollout &amp; Monitor &rarr;</a>
            <a href='/audit_explorer' target='_self' style='text-decoration:none;background:#1E293B;color:#38BDF8;padding:0.4rem 0.8rem;border-radius:6px;font-size:0.8rem;font-weight:600;'>9. Cryptographic Audit Explorer &rarr;</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# 5-Minute Live Demo Walkthrough Guide
# ---------------------------------------------------------------------------
st.markdown("### ⏱️ Recommended 5-Minute Demo Walkthrough (Section 13)")
st.markdown("""
Follow this exact sequence to demonstrate the power of the ARGUS v2 architecture:

1. **Intake & Applicability (Minute 1)**: Go to **1. Circular Inbox**, select the RBI Wire Transfer Circular (`RBI/2026/04/MD-WIRE`), view its chunked clauses. Switch bank profile in **2. Obligation Map** to `BANK-FINZAP-02` (Payments Bank) to show how ARGUS automatically marks wire rules as `NOT_APPLICABLE` and halts unnecessary rule bloat.
2. **Policy Mapping & Conflicts (Minute 2)**: Go to **3. Policy Mapping**, inspect how ARGUS maps Clause 4.2 to internal policies and immediately flags a **Conflict** against the retail wire cap.
3. **DSL & Backtest Sandbox (Minute 3)**: Go to **4. Rule Studio** to view the auto-authored YAML rule DSL and compiled OPA Rego. Move to **5. Backtest & Impact** to run backtest over 100,000 historical transactions with sub-second execution.
4. **Validation Gate & Objection Loop (Minute 3.5)**: Go to **6. Validator & Objection Loop**, run Iteration 1 to show the Validator catching the unconditioned conflict. Hit **'Resolve Objection'** to watch the Validator re-scope the rule to corporate AD-Cat 1 and produce a clean green pass report!
5. **Maker-Checker & Sub-Second Rollback (Minutes 4 - 5)**: Go to **7. Governance Approvals** to digitally sign and commit the rule with dual human control. Finally, go to **8. Rollout & Monitor**, witness the live 10% canary traffic, and click **'Simulate Metric Anomaly'** to watch ARGUS automatically roll back to the safe bundle in **480 milliseconds**!
""")
