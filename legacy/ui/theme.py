"""
ARGUS v2 UI Styling and Theme Module (Regulatory Mission Control).
Follows Part 5 specifications:
- Palette: #0B0F17, #121826, #1A2233, #263047, #E6EAF2, #8A94A8, #22D3EE, #6366F1, #22C55E, #F59E0B, #EF4444, #A78BFA
- Typography: Space Grotesk, Inter, JetBrains Mono
- Top bar with 10-stage pipeline stepper
- Always visible badge row: Draft-only · Dual-approval · PII-airlocked · Replayable
- Presenter Mode toggle and Chaos panel
"""

from pathlib import Path
import streamlit as st

THEME_DIR = Path(__file__).resolve().parent / "theme"
CSS_FILE = THEME_DIR / "argus.css"

STAGES = [
    (1, "Intake"),
    (2, "Obligation"),
    (3, "Policy Map"),
    (4, "Rule Author"),
    (5, "Backtest"),
    (6, "Impact"),
    (7, "Validation"),
    (8, "Approval"),
    (9, "Shadow"),
    (10, "Rollout"),
]


def inject_custom_css():
    """Injects argus.css and dynamic presenter mode styles."""
    if CSS_FILE.exists():
        css_content = CSS_FILE.read_text(encoding="utf-8")
    else:
        css_content = "/* CSS missing fallback */"

    presenter_class = "presenter-mode" if st.session_state.get("presenter_mode", False) else ""

    st.markdown(
        f"""
        <style>
        {css_content}
        </style>
        <div class="{presenter_class}"></div>
        """,
        unsafe_allow_html=True,
    )


def render_mission_control_header():
    """Renders the top branding and guardrail badge row."""
    st.markdown(
        """
        <div class="control-topbar">
            <div class="brand-section">
                <div class="brand-shield">A2</div>
                <div>
                    <div style="font-family: 'Space Grotesk', sans-serif; font-size: 18px; font-weight: 700; color: #E6EAF2; letter-spacing: -0.01em;">
                        ARGUS <span style="color: #22D3EE;">v2</span>
                        <span style="font-size: 13px; font-weight: 500; color: #8A94A8; margin-left: 8px;">Regulatory Mission Control</span>
                    </div>
                    <div style="font-size: 12px; color: #8A94A8;">
                        Target: <span style="color: #E6EAF2; font-weight: 600;">Meridian Bank Ltd</span> (Scheduled Commercial Bank & AD Cat-I)
                    </div>
                </div>
            </div>
            <div class="guardrail-badges">
                <span class="guardrail-chip active">● Draft-only</span>
                <span class="guardrail-chip active">● Dual-approval</span>
                <span class="guardrail-chip active">● PII-airlocked</span>
                <span class="guardrail-chip active">● Replayable</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stage_stepper(current_stage: int = 1):
    """Renders the horizontal 10-stage gated pipeline stepper."""
    stepper_html = '<div class="stage-stepper">'
    for idx, (stage_num, label) in enumerate(STAGES):
        if stage_num < current_stage:
            state_class = "completed"
            indicator = "✓"
        elif stage_num == current_stage:
            state_class = "active"
            indicator = str(stage_num)
        else:
            state_class = "pending"
            indicator = str(stage_num)

        stepper_html += f"""
        <div class="stepper-step {state_class}">
            <div class="step-num">{indicator}</div>
            <span>{label}</span>
        </div>
        """
        if idx < len(STAGES) - 1:
            stepper_html += '<div class="stepper-divider"></div>'

    stepper_html += "</div>"
    st.markdown(stepper_html, unsafe_allow_html=True)


def render_sidebar_controls():
    """Sidebar controls for Presenter Mode, Demo Autopilot, and Chaos Injection."""
    with st.sidebar:
        st.markdown(
            """
            <div style="padding-bottom: 8px; border-bottom: 1px solid #263047; margin-bottom: 12px;">
                <div style="font-family: 'Space Grotesk', sans-serif; font-size: 16px; font-weight: 700; color: #22D3EE;">
                    DEMO CONTROLS
                </div>
                <div style="font-size: 11px; color: #8A94A8;">5-Minute Winning Pitch Suite</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        presenter = st.toggle("🎤 Presenter Mode (Larger Fonts)", value=st.session_state.get("presenter_mode", False))
        st.session_state["presenter_mode"] = presenter

        st.markdown("---")
        st.markdown("##### ⚡ Demo Autopilot")
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("◀ Back", use_container_width=True):
                curr = st.session_state.get("demo_stage", 1)
                st.session_state["demo_stage"] = max(1, curr - 1)
                st.rerun()
        with col_next:
            if st.button("Advance ▶", use_container_width=True):
                curr = st.session_state.get("demo_stage", 1)
                st.session_state["demo_stage"] = min(10, curr + 1)
                st.rerun()

        st.markdown("---")
        st.markdown("##### 🚨 Chaos Injection Panel")
        st.caption("Trigger live anomaly to showcase sub-minute automatic rollback:")

        if st.button("💥 Inject Alert Flood (3x Spike)", use_container_width=True):
            st.session_state["chaos_alert_flood"] = True
            st.session_state["chaos_timestamp"] = "2026-10-26T12:45:00Z"
            st.toast("🚨 CHAOS INJECTED: Alert rate spiked 3.2x above safe SLA boundary!", icon="⚠️")

        if st.button("⏱️ Inject Latency Breach (P95 > 50ms)", use_container_width=True):
            st.session_state["chaos_latency_spike"] = True
            st.toast("🚨 CHAOS INJECTED: P95 latency degraded to 64ms!", icon="⚠️")

        if st.button("🛡️ Reset Chaos State", use_container_width=True):
            st.session_state.pop("chaos_alert_flood", None)
            st.session_state.pop("chaos_latency_spike", None)
            st.toast("✅ Chaos cleared. Engine returned to nominal baseline.", icon="✅")
