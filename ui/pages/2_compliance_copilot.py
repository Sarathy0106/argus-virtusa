"""
Page 2: Regulatory Compliance Copilot.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contracts.memory import RegulationClause
from services.regcompiler.copilot import ComplianceCopilot
from services.regcompiler.ingest import RegulationCorpusIndex

st.set_page_config(page_title="Compliance Copilot | ARGUS", page_icon="📜", layout="wide")

st.title("📜 Regulatory Compliance Copilot")
st.caption(
    "Evidence-grounded regulatory intelligence with temporal valid-time filtering and strict citation enforcement."
)


# Initialize Corpus & Copilot
@st.cache_resource
def get_copilot():
    corpus = RegulationCorpusIndex()
    # Seed canonical circulars
    corpus.add_clause(
        RegulationClause(
            id="RBI-KYC-C23",
            doc_id="RBI-MD-KYC-2016",
            title="Periodic Updation of KYC",
            clause_ref="Clause-23",
            clause_text="Regulated entities shall conduct periodic review and KYC updation every 2 years for high risk customers, 8 years for medium risk, and 10 years for low risk customers.",
            valid_from=datetime(2024, 1, 1, tzinfo=UTC),
            valid_to=datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC),
        )
    )
    corpus.add_clause(
        RegulationClause(
            id="RBI-WIRE-C12A",
            doc_id="RBI-WIRE-2024",
            title="Cross-Border Wire Transfers Reporting",
            clause_ref="Clause-12A",
            clause_text="All cross-border wire transfers exceeding USD 10,000 or INR 800,000 must include originator and beneficiary full legal names and account tokens.",
            valid_from=datetime(2024, 1, 1, tzinfo=UTC),
            valid_to=datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC),
        )
    )
    corpus.add_clause(
        RegulationClause(
            id="RBI-VCIP-C54",
            doc_id="RBI-AMEND-2026",
            title="Video-based Customer Identification Process (V-CIP)",
            clause_ref="Clause-54",
            clause_text="Video-based Customer Identification Process is recognized as equivalent to physical face-to-face verification provided geo-tagging and liveness checks pass.",
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
            valid_to=datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC),
        )
    )
    return ComplianceCopilot(corpus=corpus)


copilot = get_copilot()

col_query, col_date = st.columns([3, 1])
with col_date:
    query_date = st.date_input("Query As-Of Date:", value=datetime.now(UTC).date())
with col_query:
    sample_queries = [
        "What is the required frequency for periodic KYC updates for high risk customers?",
        "What are the reporting thresholds for cross-border wire transfers?",
        "Is Video-based Customer Identification (V-CIP) authorized as face-to-face equivalent?",
        "Can accounts be opened with unverified alien crypto tokens?",
    ]
    query = st.selectbox("Select or type compliance question:", sample_queries)

if st.button("Query Regulation Corpus", type="primary"):
    dt = datetime.combine(query_date, datetime.min.time(), tzinfo=UTC)
    res = copilot.answer_query(query, as_of_date=dt)

    if res.abstained:
        st.error(f"🛑 {res.answer}")
        st.info(
            "The system strictly abstains from guessing when no in-force regulatory circular supports the answer."
        )
    else:
        st.success("✅ Grounded & Verified Answer:")
        st.write(res.answer)

        st.subheader("Cited Regulatory Sources")
        for src in res.sources:
            with st.expander(f"📌 {src['title']} ({src['clause_ref']})"):
                st.write(f"**Clause Reference:** `{src['clause_ref']}`")
                st.write(
                    f"**In-Force Validity:** {src['valid_from'][:10]} to {src['valid_to'][:10]}"
                )
                st.write(f"**Relevance Score:** {src['score']}")
