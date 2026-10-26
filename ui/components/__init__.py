"""
Shared UI components for ARGUS Streamlit console.
"""
import json
from pathlib import Path
from typing import Any

import streamlit as st


# ---------------------------------------------------------------------------
# CSS Injection
# ---------------------------------------------------------------------------
def inject_css():
    css_path = Path(__file__).resolve().parent.parent / "styles" / "theme.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# KPI Card
# ---------------------------------------------------------------------------
def kpi_card(label: str, value: str, sub: str = "", color: str = "") -> str:
    color_class = f" {color}" if color else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value{color_class}">{value}</div>'
        f'{sub_html}'
        f'</div>'
    )


def render_kpi_row(cards: list[dict]):
    """Renders a row of KPI cards. Each dict: label, value, sub (opt), color (opt)."""
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            st.markdown(
                kpi_card(card["label"], card["value"],
                         card.get("sub", ""), card.get("color", "")),
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Badge
# ---------------------------------------------------------------------------
def badge(text: str, kind: str = "blue") -> str:
    return f'<span class="badge badge-{kind}">{text}</span>'


def render_badges(items: list[str], kind: str = "blue"):
    html = " ".join(badge(i, kind) for i in items)
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tier Pill
# ---------------------------------------------------------------------------
def tier_pill(tier: str) -> str:
    return f'<span class="tier-pill tier-{tier}">{tier}</span>'


# ---------------------------------------------------------------------------
# Token Chip
# ---------------------------------------------------------------------------
def token_chip(token: str) -> str:
    return f'<span class="token-chip">{token}</span>'


def render_token_list(tokens: list[str]):
    html = " ".join(token_chip(t) for t in tokens)
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Status Pill
# ---------------------------------------------------------------------------
def status_pill(live: bool) -> str:
    if live:
        return '<span class="status-pill status-live">● Live API</span>'
    return '<span class="status-pill status-offline">● Offline demo data</span>'


# ---------------------------------------------------------------------------
# Hash Display
# ---------------------------------------------------------------------------
def hash_display(h: str) -> str:
    return f'<div class="hash-display">{h}</div>'


# ---------------------------------------------------------------------------
# Verified / Warning banners
# ---------------------------------------------------------------------------
def verified_banner(text: str):
    st.markdown(
        f'<div class="verified-banner">✅ {text}</div>',
        unsafe_allow_html=True,
    )


def warning_banner(text: str):
    st.markdown(
        f'<div class="warning-banner">⚠️ {text}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
def page_header(title: str, subtitle: str = ""):
    sub_html = f"<p style='color:#94A3B8;font-size:0.92rem;margin-top:-0.4rem;margin-bottom:1.25rem;'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"<h1 style='font-size:1.8rem;font-weight:700;color:#F8FAFC;margin-bottom:0.25rem;letter-spacing:-0.025em;'>{title}</h1>{sub_html}",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------
def section_header(text: str):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Architecture Flow
# ---------------------------------------------------------------------------
def architecture_flow():
    steps = [
        "API Gateway",
        "PII Airlock",
        "OPA Policy Engine",
        "Agent Mesh",
        "Audit Ledger",
    ]
    parts = []
    for i, step in enumerate(steps):
        parts.append(f'<div class="arch-box">{step}</div>')
        if i < len(steps) - 1:
            parts.append('<div class="arch-arrow">→</div>')
    html = '<div class="arch-flow">' + "".join(parts) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SAR Citation rendering
# ---------------------------------------------------------------------------
def render_sar_with_citations(text: str):
    """Replace [EVID:xxx] and [CLAUSE:xxx] with styled chips."""
    import re
    def replace_citation(m):
        return f'<span class="citation-chip">[{m.group(1)}:{m.group(2)}]</span>'
    html = re.sub(r'\[(EVID|CLAUSE):([^\]]+)\]', replace_citation, text)
    html = html.replace("\n", "<br>")
    st.markdown(
        f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:0.9rem;'
        f'line-height:1.75;padding:1.25rem;background:#111827;border:1px solid #1E293B;'
        f'border-radius:10px;color:#CBD5E1;box-shadow:0 4px 16px rgba(0,0,0,0.4);white-space:pre-wrap;">{html}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Plotly Network Graph
# ---------------------------------------------------------------------------
def plotly_network_graph(case: dict):
    try:
        import networkx as nx
        import plotly.graph_objects as go

        graph_data = case.get("case_graph", {})
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        G = nx.Graph()
        for n in nodes:
            G.add_node(n["id"], node_type=n["type"])
        for e in edges:
            G.add_edge(e["source"], e["target"], relation=e.get("relation", ""))

        pos = nx.spring_layout(G, seed=42, k=2)

        # Node colors by type (vivid high-tech cyber palette)
        color_map = {
            "TRANSACTION": "#3B82F6",
            "ACCOUNT": "#10B981",
            "COUNTERPARTY": "#F59E0B",
            "DEVICE": "#A855F7",
        }

        edge_x, edge_y = [], []
        for u, v in G.edges():
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(width=1.5, color="#334155"),
            hoverinfo="none",
        )

        node_traces = {}
        for n in G.nodes():
            ntype = G.nodes[n].get("node_type", "ACCOUNT")
            if ntype not in node_traces:
                node_traces[ntype] = {"x": [], "y": [], "text": [], "color": color_map.get(ntype, "#64748B")}
            node_traces[ntype]["x"].append(pos[n][0])
            node_traces[ntype]["y"].append(pos[n][1])
            # Shorten label
            label = n.split("_", 1)[-1] if "_" in n else n
            node_traces[ntype]["text"].append(label)

        data = [edge_trace]
        for ntype, nt in node_traces.items():
            data.append(go.Scatter(
                x=nt["x"], y=nt["y"], mode="markers+text",
                marker=dict(size=16, color=nt["color"], line=dict(width=2, color="#0B0F19")),
                text=nt["text"], textposition="top center",
                textfont=dict(size=10, family="JetBrains Mono, monospace", color="#F8FAFC"),
                name=ntype, hovertext=nt["text"], hoverinfo="text",
            ))

        fig = go.Figure(
            data=data,
            layout=go.Layout(
                showlegend=True,
                hovermode="closest",
                margin=dict(b=20, l=10, r=10, t=30),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                paper_bgcolor="#111827",
                plot_bgcolor="#111827",
                height=400,
                legend=dict(
                    font=dict(size=11, color="#CBD5E1"),
                    bgcolor="rgba(17, 24, 39, 0.8)",
                    bordercolor="#1E293B",
                    borderwidth=1,
                ),
            ),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Graph render error: {e}")


# ---------------------------------------------------------------------------
# Ledger block expander
# ---------------------------------------------------------------------------
def render_ledger_block(block: dict, show_copy: bool = True):
    seq = block.get("seq", "?")
    event = block.get("event_type", "UNKNOWN")
    signer = block.get("signer", "unknown")
    with st.expander(f"Block #{seq} — {event} (Signer: {signer})"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Entity ID**")
            st.code(block.get("entity_id", ""), language="text")
            st.markdown("**Recorded At**")
            st.code(block.get("recorded_at", ""), language="text")
        with col2:
            st.markdown("**Block Hash**")
            st.code(block.get("block_hash", ""), language="text")
            st.markdown("**Parent Hash**")
            st.code(block.get("prev_hash", ""), language="text")
        st.markdown("**Payload**")
        payload_str = json.dumps(block.get("payload", {}), indent=2)
        st.code(payload_str, language="json")
        if show_copy:
            if st.button(f"Copy block #{seq}", key=f"copy_block_{seq}"):
                st.toast(f"Block #{seq} copied to clipboard ✓")


# ---------------------------------------------------------------------------
# V2 10-Stage Pipeline Stepper
# ---------------------------------------------------------------------------
def render_ten_stage_pipeline(active_stage: int = 1):
    stages = [
        {"num": 1, "name": "Intake", "agent": "IntakeAgent"},
        {"num": 2, "name": "Obligations", "agent": "ObligationAgent"},
        {"num": 3, "name": "Policy Map", "agent": "PolicyMapperAgent"},
        {"num": 4, "name": "Rule Author", "agent": "RuleAuthorAgent"},
        {"num": 5, "name": "Backtest", "agent": "BacktestAgent"},
        {"num": 6, "name": "Impact", "agent": "ImpactAgent"},
        {"num": 7, "name": "Validation", "agent": "ValidatorAgent"},
        {"num": 8, "name": "Approval", "agent": "MakerChecker"},
        {"num": 9, "name": "Shadow", "agent": "DeploymentAgent"},
        {"num": 10, "name": "Rollout", "agent": "MonitorAgent"},
    ]
    parts = []
    for s in stages:
        num = s["num"]
        name = s["name"]
        if num < active_stage:
            cls = "arch-box"
            status_dot = "<span style='color:#34D399;font-size:0.7rem;'>●</span>"
            border_col = "border:1px solid rgba(16,185,129,0.4);"
            bg_col = "background:linear-gradient(145deg, #064E3B 0%, #0F172A 100%);"
        elif num == active_stage:
            cls = "arch-box"
            status_dot = "<span style='color:#60A5FA;font-size:0.7rem;animation:pulse 1.5s infinite;'>●</span>"
            border_col = "border:1px solid #3B82F6;box-shadow:0 0 16px rgba(59,130,246,0.4);"
            bg_col = "background:linear-gradient(145deg, #1E3A8A 0%, #111827 100%);"
        else:
            cls = "arch-box"
            status_dot = "<span style='color:#475569;font-size:0.7rem;'>○</span>"
            border_col = "border:1px solid #1E293B;"
            bg_col = "background:#0D1322;"

        box_html = (
            f"<div class='{cls}' style='{border_col}{bg_col}min-width:105px;padding:0.6rem 0.3rem;'>"
            f"<div style='font-size:0.68rem;color:#94A3B8;font-weight:700;'>STAGE {num}</div>"
            f"<div style='font-size:0.8rem;font-weight:700;color:#F8FAFC;margin:0.15rem 0;'>{status_dot} {name}</div>"
            f"<div style='font-size:0.65rem;color:#64748B;'>{s['agent']}</div>"
            f"</div>"
        )
        parts.append(box_html)

    arrow_html = "<div class='arch-arrow' style='color:#334155;font-size:0.9rem;'>→</div>"
    flow_html = f"<div class='arch-flow' style='gap:0.15rem;'>{arrow_html.join(parts)}</div>"
    st.markdown(flow_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Bank Profile Banner
# ---------------------------------------------------------------------------
def render_bank_profile_header():
    from ui.services.client_v2 import get_active_bank_profile, get_bank_profiles, set_active_bank_profile
    profile = get_active_bank_profile()
    profiles = get_bank_profiles()

    col_info, col_select = st.columns([3, 1])
    with col_info:
        st.markdown(
            f"<div style='background:#111827;border:1px solid #1E293B;border-radius:10px;padding:0.85rem 1.25rem;display:flex;align-items:center;gap:1rem;margin-bottom:1rem;'>"
            f"<div style='font-size:1.8rem;'>🏦</div>"
            f"<div>"
            f"<div style='font-size:0.72rem;font-weight:700;color:#60A5FA;text-transform:uppercase;letter-spacing:0.08em;'>Active Institution Profile</div>"
            f"<div style='font-size:1.1rem;font-weight:800;color:#F8FAFC;'>{profile['name']}</div>"
            f"<div style='font-size:0.78rem;color:#94A3B8;margin-top:0.15rem;'>{profile['badge']} · Tier: <code style='color:#FCD34D;'>{profile['tier']}</code></div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_select:
        opts = [p["id"] for p in profiles]
        idx = opts.index(profile["id"]) if profile["id"] in opts else 0
        new_prof = st.selectbox(
            "Switch Institution Profile",
            opts,
            index=idx,
            format_func=lambda x: next((p["short_name"] for p in profiles if p["id"] == x), x),
            key="bank_profile_switcher",
        )
        if new_prof != profile["id"]:
            set_active_bank_profile(new_prof)
            st.rerun()


# ---------------------------------------------------------------------------
# Mapping Type Pill
# ---------------------------------------------------------------------------
def mapping_type_pill(mtype: str) -> str:
    color_map = {
        "GAP": ("#EF4444", "rgba(239,68,68,0.15)", "rgba(239,68,68,0.35)"),
        "CONFLICT": ("#F59E0B", "rgba(245,158,11,0.15)", "rgba(245,158,11,0.35)"),
        "OVERLAP": ("#A855F7", "rgba(168,85,247,0.15)", "rgba(168,85,247,0.35)"),
        "ALIGNED": ("#10B981", "rgba(16,185,129,0.15)", "rgba(16,185,129,0.35)"),
    }
    fg, bg, border = color_map.get(mtype, ("#94A3B8", "#1E293B", "#334155"))
    return (
        f"<span style='background:{bg};color:{fg};border:1px solid {border};"
        f"padding:0.2rem 0.65rem;border-radius:4px;font-weight:700;font-size:0.75rem;"
        f"font-family:\"JetBrains Mono\", monospace;'>{mtype}</span>"
    )

