"""
Page 4: Rule Studio & Traceability Graph (Stage 4).
Authors draft rule changes in YAML Rule DSL, compiles bit-for-bit Rego code,
synthesizes synthetic test cases, and renders the end-to-end Traceability Graph.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from services.orchestrator.v2_state_machine import RegulatoryRuleOrchestrator
from ui.theme import inject_custom_css, render_brand_header, render_pipeline_stepper

st.set_page_config(page_title="Rule Studio | ARGUS v2", page_icon="⚙️", layout="wide")
inject_custom_css()
render_brand_header(current_stage_num=4, current_stage_name="RULE_AUTHORING")
render_pipeline_stepper(active_stage=4)


if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RegulatoryRuleOrchestrator()

orch = st.session_state.orchestrator

# Ensure mappings exist
if "policy_mapping" not in st.session_state:
    SAMPLE_CIRCULAR = """
Reserve Bank of India
Notification: RBI/2024-25/118
Master Direction – Enhanced Risk Management Framework for Immediate and UPI Transactions

Section 2: High-Value Immediate Transfer Cooling Period
All regulated entities shall enforce a mandatory cooling period of 4 hours for any retail immediate payment
or UPI transaction where the single transaction amount meets or exceeds INR 50,000.
"""
    intake = orch.intake_agent.process_circular("RBI-2024-118", "UPI Risk Management", SAMPLE_CIRCULAR)
    obls = orch.obligation_agent.extract_obligations(intake["clauses"], st.session_state.bank_profile)
    mapping = orch.policy_mapper_agent.map_obligations(obls, bank_id=st.session_state.bank_profile.bank_id)
    st.session_state.obligations = obls
    st.session_state.policy_mapping = mapping

target_obl = st.session_state.obligations[0]
target_map = st.session_state.policy_mapping.mappings[0]

c_sel, c_btn = st.columns([1.2, 0.8])
with c_sel:
    iteration_choice = st.radio("Authoring Mode", ["Corrected Production Draft (Iteration 2)", "Flawed Preliminary Draft (Iteration 1)"])
    it_val = 1 if "Flawed" in iteration_choice else 2

with c_btn:
    if st.button("🔨 Author Rule in Rule DSL & Compile Rego (Stage 4)", type="primary"):
        with st.spinner("Authoring Rule DSL and compiling Rego policies..."):
            rule_def, rego, tests = orch.rule_author_agent.author_rule(
                obligation=target_obl,
                mapping=target_map,
                iteration=it_val,
            )
            st.session_state.rule_definition = rule_def
            st.session_state.compiled_rego = rego
            st.session_state.compiled_tests = tests
            st.session_state.traceability_graph = orch.compiler.build_traceability_graph(rule_def)
        st.success(f"Rule '{rule_def.rule_name}' authored in Rule DSL and compiled to Rego!")

if "rule_definition" in st.session_state:
    r_def = st.session_state.rule_definition
    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rule Name", r_def.rule_name)
    m2.metric("Version", r_def.version)
    m3.metric("Draft Status", r_def.draft_status)
    m4.metric("Clause Citations", len(r_def.citations))

    tab1, tab2, tab3, tab4 = st.tabs([
        "📄 Declarative Rule DSL (YAML)",
        "🛡️ Compiled Rego Policy (OPA)",
        "🧪 Synthetic Unit Tests",
        "🌐 Clause-to-Rule Traceability Graph",
    ])

    with tab1:
        st.markdown("**Declarative YAML Rule DSL Specification:**")
        st.code(r_def.to_yaml(), language="yaml")

    with tab2:
        st.markdown("**Deterministic Open Policy Agent (Rego) Code:**")
        st.code(st.session_state.compiled_rego, language="rego")

    with tab3:
        st.markdown("**Synthesized Rego Unit Test Suite:**")
        st.code(st.session_state.compiled_tests, language="rego")
        st.write("**Local Sandbox Test Execution:**")
        passed, total, fails = orch.compiler.run_synthetic_tests(r_def)
        if passed == total:
            st.success(f"✅ All {passed}/{total} synthetic unit tests passed locally.")
        else:
            st.error(f"❌ {passed}/{total} unit tests passed. Failures: {fails}")

    with tab4:
        st.markdown("**End-to-End Regulatory Traceability Graph:**")
        st.info("Queryable audit link: Regulatory Clause ➔ Obligation ➔ Bank Policy ➔ Rule DSL ➔ OPA Rego ➔ Test Case")
        graph = st.session_state.traceability_graph
        
        # Render Mermaid Diagram
        mermaid_lines = ["graph LR"]
        for node in graph["nodes"]:
            nid = node["id"].replace("-", "_").replace(".", "_")
            mermaid_lines.append(f'    {nid}["{node["label"]}"]')
        for edge in graph["edges"]:
            f = edge["from"].replace("-", "_").replace(".", "_")
            t = edge["to"].replace("-", "_").replace(".", "_")
            mermaid_lines.append(f"    {f} -->|{edge['relation']}| {t}")

        st.markdown(f"```mermaid\n{chr(10).join(mermaid_lines)}\n```")
