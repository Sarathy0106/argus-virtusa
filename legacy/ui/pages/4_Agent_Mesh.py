"""
Page 4: Live Agent Mesh & Objection Loop Visualizer.
Signature moment: Animated nodes, signed Agent Cards (A2A), cryptographic key fingerprints,
token budget meters, and the Objection Loop routing arrow lighting up amber!
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
import streamlit.components.v1 as components
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator
from ui.theme import (
    inject_custom_css,
    render_mission_control_header,
    render_sidebar_controls,
    render_stage_stepper,
)

st.set_page_config(page_title="Agent Mesh | ARGUS v2", page_icon="🕸️", layout="wide")
inject_custom_css()
render_sidebar_controls()
render_mission_control_header()
render_stage_stepper(current_stage=4)

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

st.markdown("### 🕸️ Live Multi-Agent Mesh & Objection Loop")
st.caption("A2A Signed Protocol: Each agent runs with an Ed25519 cryptographic identity card, brokered skills, and token limits. The cyclic Objection Loop re-routes drafts on validation failure.")

# Agent status summary cards
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(
        """
        <div class="argus-card" style="padding: 12px;">
            <div style="font-size: 11px; color: #8A94A8;">AGENT 1</div>
            <div style="font-weight: 700; color: #22D3EE;">Intake Agent</div>
            <div style="font-size: 11px; color: #22C55E; margin-top: 4px;">● Signed Card ✓</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        """
        <div class="argus-card" style="padding: 12px;">
            <div style="font-size: 11px; color: #8A94A8;">AGENT 2</div>
            <div style="font-weight: 700; color: #22D3EE;">Obligation Agent</div>
            <div style="font-size: 11px; color: #22C55E; margin-top: 4px;">● Signed Card ✓</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        """
        <div class="argus-card" style="padding: 12px;">
            <div style="font-size: 11px; color: #8A94A8;">AGENT 3</div>
            <div style="font-weight: 700; color: #22D3EE;">Policy Mapper</div>
            <div style="font-size: 11px; color: #22C55E; margin-top: 4px;">● Z3 Prover Active</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        """
        <div class="argus-card" style="padding: 12px;">
            <div style="font-size: 11px; color: #8A94A8;">AGENT 4</div>
            <div style="font-weight: 700; color: #F59E0B;">Validator Gate</div>
            <div style="font-size: 11px; color: #F59E0B; margin-top: 4px;">⚠️ Objection Raised</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col5:
    st.markdown(
        """
        <div class="argus-card" style="padding: 12px;">
            <div style="font-size: 11px; color: #8A94A8;">AGENT 5</div>
            <div style="font-weight: 700; color: #22D3EE;">Rule Author</div>
            <div style="font-size: 11px; color: #22C55E; margin-top: 4px;">● Iteration 2/3</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("#### 🔄 Dynamic Agent Communication Graph & Objection Routing")

# Interactive SVG / HTML Canvas rendering the Live Agent Mesh with Objection Loop
mesh_html = """
<div style="background: #121826; border: 1px solid #263047; border-radius: 12px; padding: 24px; position: relative; overflow: hidden; width: 100%; height: 380px;">
    <svg width="100%" height="100%" viewBox="0 0 900 320" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="cyanGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#22D3EE" stop-opacity="0.8"/>
                <stop offset="100%" stop-color="#6366F1" stop-opacity="0.8"/>
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
        </defs>

        <!-- Forward Connecting Edges -->
        <path d="M 120 160 L 260 160" stroke="#263047" stroke-width="3" stroke-dasharray="6 4"/>
        <path d="M 260 160 L 400 160" stroke="#263047" stroke-width="3" stroke-dasharray="6 4"/>
        <path d="M 400 160 L 540 160" stroke="#263047" stroke-width="3"/>
        <path d="M 540 160 L 680 160" stroke="#263047" stroke-width="3"/>
        <path d="M 680 160 L 820 160" stroke="#263047" stroke-width="3"/>

        <!-- OBJECTION LOOP CONDITIONAL EDGE (Amber Glowing Arc) -->
        <path d="M 680 130 C 600 30, 480 30, 400 130" fill="none" stroke="#F59E0B" stroke-width="3.5" filter="url(#glow)"/>
        <!-- Animated Packet along Objection Arc -->
        <circle cx="540" cy="55" r="5" fill="#F59E0B">
            <animate attributeName="opacity" values="0.3;1;0.3" dur="1.5s" repeatCount="indefinite"/>
        </circle>
        <text x="540" y="42" fill="#F59E0B" font-family="Space Grotesk, sans-serif" font-size="12" font-weight="700" text-anchor="middle">
            OBJECTION LOOP (Iteration 1 ➔ 2: Conflict Re-route)
        </text>

        <!-- Node 1: Intake Agent -->
        <circle cx="120" cy="160" r="36" fill="#1A2233" stroke="#22D3EE" stroke-width="2.5"/>
        <text x="120" y="155" fill="#E6EAF2" font-family="Space Grotesk, sans-serif" font-size="12" font-weight="700" text-anchor="middle">Intake</text>
        <text x="120" y="172" fill="#8A94A8" font-family="JetBrains Mono, monospace" font-size="9" text-anchor="middle">Airlock</text>

        <!-- Node 2: Obligation Agent -->
        <circle cx="260" cy="160" r="36" fill="#1A2233" stroke="#22D3EE" stroke-width="2.5"/>
        <text x="260" y="155" fill="#E6EAF2" font-family="Space Grotesk, sans-serif" font-size="12" font-weight="700" text-anchor="middle">Obligation</text>
        <text x="260" y="172" fill="#8A94A8" font-family="JetBrains Mono, monospace" font-size="9" text-anchor="middle">App-Filter</text>

        <!-- Node 3: Policy Mapper -->
        <circle cx="400" cy="160" r="38" fill="#1A2233" stroke="#22D3EE" stroke-width="3" filter="url(#glow)"/>
        <text x="400" y="155" fill="#22D3EE" font-family="Space Grotesk, sans-serif" font-size="12" font-weight="700" text-anchor="middle">Policy Map</text>
        <text x="400" y="172" fill="#22C55E" font-family="JetBrains Mono, monospace" font-size="9" text-anchor="middle">Z3 Prover</text>

        <!-- Node 4: Rule Author -->
        <circle cx="540" cy="160" r="36" fill="#1A2233" stroke="#22D3EE" stroke-width="2.5"/>
        <text x="540" y="155" fill="#E6EAF2" font-family="Space Grotesk, sans-serif" font-size="12" font-weight="700" text-anchor="middle">Rule Author</text>
        <text x="540" y="172" fill="#8A94A8" font-family="JetBrains Mono, monospace" font-size="9" text-anchor="middle">DSL / Rego</text>

        <!-- Node 5: Validator Gate -->
        <circle cx="680" cy="160" r="38" fill="#1A2233" stroke="#F59E0B" stroke-width="3" filter="url(#glow)"/>
        <text x="680" y="155" fill="#F59E0B" font-family="Space Grotesk, sans-serif" font-size="12" font-weight="700" text-anchor="middle">Validator</text>
        <text x="680" y="172" fill="#F59E0B" font-family="JetBrains Mono, monospace" font-size="9" text-anchor="middle">GATE REJECT</text>

        <!-- Node 6: Approval -->
        <circle cx="820" cy="160" r="36" fill="#1A2233" stroke="#6366F1" stroke-width="2"/>
        <text x="820" y="155" fill="#E6EAF2" font-family="Space Grotesk, sans-serif" font-size="12" font-weight="700" text-anchor="middle">Human Sign</text>
        <text x="820" y="172" fill="#8A94A8" font-family="JetBrains Mono, monospace" font-size="9" text-anchor="middle">Dual-Key</text>
    </svg>
</div>
"""
components.html(mesh_html, height=400)

st.markdown("#### 📨 Cryptographic A2A Message Packet Inspector")
st.markdown(
    """
    Every inter-agent message carries: `trace_id`, `case_id`, `clause_ids[]`, `evidence_ids[]`, `input_hash`, and an `Ed25519 signature`.
    """
)

sample_packet = {
    "protocol": "A2A/2.0",
    "trace_id": "trc_9a4f210d7b",
    "source_agent": "agent.validator",
    "target_stage": "STAGE_3_POLICY_MAPPING",
    "action": "OBJECTION_REJECT_AND_REROUTE",
    "iteration": 1,
    "max_iterations": 3,
    "objection": {
        "code": "ACTIVE_CONFLICT_UNRESOLVED",
        "existing_rule": "R-CASH-014",
        "z3_counter_example": "₹1,000,000 cash deposit for Risk Band C customer",
        "action_divergence": "BLOCK vs ENHANCED_REVIEW",
    },
    "signature": "ed25519_sig_val_8a92f03c88192b0c112e",
}

st.json(sample_packet)
