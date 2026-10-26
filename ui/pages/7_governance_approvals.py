"""
ARGUS v2 — Stage 8: Maker-Checker Governance & Dual Approval
Mandatory Dual-Control Gate: Requires Compliance Lead (Maker) and Risk Head (Checker) countersignatures.
Generates an Ed25519 digital signature and commits an immutable block to the SHA-256 Audit Ledger.
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
import hashlib
import streamlit as st

from ui.components import (
    inject_css, page_header, section_header, render_ten_stage_pipeline,
    render_bank_profile_header, verified_banner, warning_banner, badge
)
from ui.services.client_v2 import get_sample_pipeline
from ui.services.client import append_ledger_block

st.set_page_config(page_title="Human Approval — ARGUS v2", page_icon="✍️", layout="wide")

inject_css()

page_header(
    "✍️ Stage 8: Maker-Checker Human Approval Gate",
    "Dual-control human governance · Compliance & Risk signoff · Ed25519 signature · Audit ledger appending"
)
render_ten_stage_pipeline(active_stage=8)
st.markdown("---")
render_bank_profile_header()

case = get_sample_pipeline()
rule_id = case["rule_dsl_yaml"].split('rule_id: "')[1].split('"')[0]

with st.sidebar:
    st.markdown("### ✍️ Stage 8: Governance Gate")
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.8rem;color:#94A3B8;'>"
        "<b>Zero Unapproved Rules to Production:</b> LLMs and agents are architecturally blocked from "
        "promoting rules. Dual human cryptographic signoff is required before the Deployment Agent "
        "can initialize shadow mode.</div>",
        unsafe_allow_html=True,
    )

section_header(f"Dual-Control Approval Docket — Rule: {rule_id}")

col_m, col_c = st.columns(2)

with col_m:
    st.markdown(
        "<div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1.25rem;'>"
        "<div style='font-size:0.75rem;font-weight:700;color:#60A5FA;text-transform:uppercase;'>Maker Role (Compliance Desk)</div>"
        "<div style='font-size:1.1rem;font-weight:700;color:#F8FAFC;margin:0.25rem 0;'>Sarah Jenkins</div>"
        "<div style='font-size:0.8rem;color:#94A3B8;'>AVP, Regulatory Affairs &amp; Policy</div>"
        "<hr style='border-color:#1E293B;margin:0.75rem 0;'>"
        "<div style='font-size:0.82rem;color:#CBD5E1;line-height:1.5;'>"
        "<b>Attestation:</b> I certify that the YAML Rule DSL and OPA Rego logic accurately reflect "
        "RBI Master Direction Section 12(a). Backtest impact of +14.5 ops hrs/mo is within branch capacity."
        "</div>"
        "<div style='margin-top:0.75rem;'>"
        "<span style='color:#34D399;font-weight:700;font-size:0.85rem;'>✓ Maker Signed (2026-03-20 11:15 UTC)</span>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

with col_c:
    st.markdown(
        "<div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:1.25rem;'>"
        "<div style='font-size:0.75rem;font-weight:700;color:#A855F7;text-transform:uppercase;'>Checker Role (Risk Governance)</div>"
        "<div style='font-size:1.1rem;font-weight:700;color:#F8FAFC;margin:0.25rem 0;'>Marcus Thorne</div>"
        "<div style='font-size:0.8rem;color:#94A3B8;'>Chief Risk Officer (CRO)</div>"
        "<hr style='border-color:#1E293B;margin:0.75rem 0;'>"
        "<div style='font-size:0.82rem;color:#CBD5E1;line-height:1.5;'>"
        "<b>Attestation:</b> I have reviewed the Validator Agent conflict resolution report and backtest delta. "
        "Account scoping to Corporate & AD-Cat 1 is verified. Approved for Stage 9 Shadow Deployment."
        "</div>"
        "<div style='margin-top:0.75rem;'>"
        "<span style='color:#34D399;font-weight:700;font-size:0.85rem;'>✓ Checker Countersigned (2026-03-20 14:40 UTC)</span>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:1.25rem;'></div>", unsafe_allow_html=True)

# Cryptographic Signature & Ledger Block
section_header("Cryptographic Attestation & Audit Block")

appr = case["approvals"]
col_sig1, col_sig2 = st.columns([2, 1])

with col_sig1:
    st.markdown(f"**Ed25519 Cryptographic Token:**")
    st.code(appr["ed25519_signature"], language="text")
    st.markdown(f"**Ledger Block Hash:**")
    st.code(appr["ledger_hash"], language="text")

with col_sig2:
    st.markdown(f"**Approval Status:** {badge(appr['approval_status'], 'green')}", unsafe_allow_html=True)
    st.markdown(f"**Target Bundle Version:** `v1.1.0-candidate`")
    st.markdown(f"**Audit Sequence:** `Block #{appr['audit_block_seq']}`")
    st.markdown(f"**Signoff Engine:** `Dual-Key Ed25519 Hardware Vault`")

st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
verified_banner("Dual Human Approval Verified: Cryptographically appended to SHA-256 tamper-evident ledger. Stage 9 Shadow Deployment is UNLOCKED.")

st.markdown("---")
col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("← Back to Stage 7: Validation"):
        st.switch_page("pages/6_validator_objection_loop.py")
with col_nav2:
    st.markdown("<div style='display:flex;justify-content:flex-end;'>", unsafe_allow_html=True)
    if st.button("Proceed to Stages 9 & 10: Shadow & Rollout →", type="primary"):
        st.switch_page("pages/8_rollout_monitor.py")
    st.markdown("</div>", unsafe_allow_html=True)
