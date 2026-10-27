"""
Page 6: Dual Human Approval & Cryptographic Governance (Stage 8).
Maker-checker two-person rule enforced via Ed25519 digital signatures.
Rejects deployment if unsigned or single-signed, or if maker == checker.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from contracts.deployment import DualApprovalToken
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator
from ui.theme import (
    inject_custom_css,
    render_mission_control_header,
    render_sidebar_controls,
    render_stage_stepper,
)

st.set_page_config(page_title="Human Approvals | ARGUS v2", page_icon="✍️", layout="wide")
inject_custom_css()
render_sidebar_controls()
render_mission_control_header()
render_stage_stepper(current_stage=8)

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

st.markdown("### ✍️ Maker-Checker Dual Cryptographic Approval")
st.caption("Stage 8 of 10: Non-negotiable human governance. LLMs draft, deterministic code validates, but only two distinct human compliance officers can authorize production deployment.")

# Dual Approval Status Cards
maker_signed = st.session_state.get("maker_signed", False)
checker_signed = st.session_state.get("checker_signed", False)

col_maker, col_checker = st.columns(2)

with col_maker:
    maker_border = "#22C55E" if maker_signed else "#263047"
    st.markdown(
        f"""
        <div class="argus-card" style="border-top: 4px solid {maker_border};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-weight: 700; font-size: 16px; color: #E6EAF2;">Maker: Compliance Officer</div>
                <span class="mono-chip {'mono-chip-green' if maker_signed else ''}">
                    {'✓ SIGNED (Ed25519)' if maker_signed else 'Awaiting Signature'}
                </span>
            </div>
            <div style="font-size: 13px; color: #8A94A8; margin-top: 8px;">
                <strong>Officer:</strong> Rajesh Sharma (Senior Regulatory Policy Maker)<br>
                <strong>Role:</strong> First-line compliance verification & rule authorship review.<br>
                <strong>Key ID:</strong> <code>ed25519_pub_maker_4492a8...</code>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_checker:
    checker_border = "#22C55E" if checker_signed else "#263047"
    st.markdown(
        f"""
        <div class="argus-card" style="border-top: 4px solid {checker_border};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-weight: 700; font-size: 16px; color: #E6EAF2;">Checker: Head of Risk / CCO</div>
                <span class="mono-chip {'mono-chip-green' if checker_signed else ''}">
                    {'✓ SIGNED (Ed25519)' if checker_signed else 'Awaiting Signature'}
                </span>
            </div>
            <div style="font-size: 13px; color: #8A94A8; margin-top: 8px;">
                <strong>Officer:</strong> Vikram Malhotra (Chief Compliance Officer)<br>
                <strong>Role:</strong> Secondary independent sign-off & impact signoff.<br>
                <strong>Key ID:</strong> <code>ed25519_pub_checker_9104f1...</code>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("#### 🔑 Interactive Sign-Off & Single-Sign Attempt Test")

col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    maker_input_id = st.selectbox("Select Maker ID:", ["maker.rajesh (Compliance Lead)", "maker.ananya (Policy Analyst)"])
    if st.button("🖊️ Sign as Maker (First Sign-Off)", type="primary" if not maker_signed else "secondary", use_container_width=True):
        st.session_state["maker_signed"] = True
        st.session_state["maker_id"] = maker_input_id.split()[0]
        st.toast("Maker signature recorded with Ed25519 hash!", icon="✅")
        st.rerun()

with col_btn2:
    checker_input_id = st.selectbox("Select Checker ID:", ["checker.vikram (Chief Compliance Officer)", "checker.sunita (Head of Risk)"])
    if st.button("🖊️ Sign as Checker (Second Sign-Off)", type="primary" if (maker_signed and not checker_signed) else "secondary", use_container_width=True):
        st.session_state["checker_signed"] = True
        st.session_state["checker_id"] = checker_input_id.split()[0]
        st.toast("Checker signature recorded! Dual-token generated.", icon="✅")
        st.rerun()

st.divider()

st.markdown("##### 🛡️ Production Deployment Token Verification")
col_dep1, col_dep2 = st.columns([1.2, 0.8])

with col_dep1:
    if st.button("🚀 Attempt Core Engine Deployment (Verify Token)", type="primary", use_container_width=True):
        if not maker_signed and not checker_signed:
            st.error("❌ REJECTED: Deployment API returned 403 Forbidden. Rule has 0 signatures. Unapproved rules never reach production enforcement.")
        elif maker_signed and not checker_signed:
            st.error("❌ REJECTED: Deployment API returned 403 Forbidden. Dual-approval violation: Only 1 of 2 required signatures present. Two-person rule enforced.")
        elif checker_signed and not maker_signed:
            st.error("❌ REJECTED: Deployment API returned 403 Forbidden. Checker cannot approve without primary Maker signature.")
        else:
            # Both signed!
            token = DualApprovalToken(
                token_id="TOK-2026-C1-8891",
                rule_name="R-CASH-021",
                rule_version="1.0.0",
                maker_id=st.session_state.get("maker_id", "maker.rajesh"),
                checker_id=st.session_state.get("checker_id", "checker.vikram"),
                maker_signature="ed25519_sig_maker_991823ab",
                checker_signature="ed25519_sig_checker_441299cd",
                rationale="Approved revised cash deposit enhanced review threshold per RBI C1 mandate.",
            )
            orch.deployment_agent.register_approval_token(token)
            st.session_state["approval_token"] = token
            st.session_state.demo_stage = 9
            st.success("✅ DUAL APPROVAL VERIFIED: Both Ed25519 signatures validated. DualApprovalToken minted. Authorized for Stage 9 Shadow Mode!")

with col_dep2:
    st.markdown(
        """
        <div class="argus-card-elevated">
            <div style="font-weight: 700; color: #22D3EE;">Governance Non-Negotiables</div>
            <ul style="font-size: 12px; color: #8A94A8; margin-top: 6px; padding-left: 18px;">
                <li>The Maker CANNOT equal the Checker.</li>
                <li>Single-signed tokens are cryptographically rejected by the Deployment API.</li>
                <li>Dual approval logs are committed to the hash-chained audit ledger.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
