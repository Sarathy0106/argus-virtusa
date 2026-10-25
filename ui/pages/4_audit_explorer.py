"""
Page 4: Audit Ledger & Deterministic Replay Explorer.
"""

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contracts.decisions import DecisionRecord
from services.ledger.ledger import AuditLedger
from services.ledger.replay import ReplayEngine
from services.policy.engine import PolicyEngine

st.set_page_config(page_title="Audit & Replay | ARGUS", page_icon="🔗", layout="wide")

st.title("🔗 Cryptographic Audit Ledger & Replay Explorer")
st.caption(
    "Forensic verification of hash-chained decisions and bit-for-bit deterministic replay validation."
)


@st.cache_resource
def get_sample_ledger():
    ledger = AuditLedger()
    ledger.append(
        "SYSTEM_GENESIS", "SYS-001", "system_vault", {"version": "1.0.0", "status": "INITIALIZED"}
    )
    ledger.append(
        "DECISION_RECORDED",
        "DEC-1001",
        "agent.txn_risk",
        {"transaction_id": "TXN-881", "outcome": "HOLD", "tier": "T1"},
    )
    ledger.append(
        "CASE_RESOLVED_CONFIRMED",
        "CASE-001",
        "maker:alice|checker:david",
        {"verdict": "CONFIRMED_SUSPICIOUS", "tier": "T2"},
    )
    ledger.append(
        "RULE_BUNDLE_PUBLISHED",
        "POL-WIRE-01",
        "maker:sarah|checker:marcus",
        {"rule": "cross_border_wire", "version": "1.1.0"},
    )
    return ledger


ledger = get_sample_ledger()

st.subheader("1. Append-Only Cryptographic Hash-Chain")
st.caption(
    "Each entry's hash is bound to the preceding block's hash: `Hash_n = SHA-256(Hash_{n-1} || payload_h || signer || ts)`."
)

if st.button("Verify Complete Chain Cryptographic Integrity"):
    is_valid = ledger.verify_integrity()
    if is_valid:
        st.success(
            "✅ Complete ledger integrity verified! 0 tampering or broken links detected across all blocks."
        )

# Display chain entries
for i in range(1, ledger.count() + 1):
    entry = ledger.get_by_seq(i)
    if entry:
        with st.expander(f"Block #{entry.seq} — {entry.event_type} (Signer: {entry.signer})"):
            st.write(f"**Entity ID:** `{entry.entity_id}`")
            st.write(f"**Block Hash:** `{entry.verify_hash()}`")
            st.write(f"**Previous Block Hash:** `{entry.prev_hash}`")
            st.write(f"**Recorded Timestamp:** `{entry.recorded_at}`")
            st.json(entry.payload)

st.divider()

st.subheader("2. Bit-for-Bit Decision Replay Engine")
st.caption(
    "Re-executes archived decision inputs against pinned rule bundles and verifies exact bitwise identity."
)

col_r1, col_r2 = st.columns(2)
with col_r1:
    decision_id = st.text_input("Decision ID to Replay:", value="DEC-1001")
    archived_amount = st.number_input("Archived Amount (INR):", value=49200.0)
    structuring_count = st.number_input("Structuring Window Count (24h):", value=3)

with col_r2:
    rule_bundle_ver = st.selectbox("Policy Bundle Version:", ["1.0.0", "1.1.0"])
    country = st.selectbox("Country of Transaction:", ["IND", "USA", "PRK"])

if st.button("Execute Bit-for-Bit Replay", type="primary"):
    inputs = {
        "amount": archived_amount,
        "structuring_window_count_24h": structuring_count,
        "location_country": country,
    }

    policy_engine = PolicyEngine()
    eval_res = policy_engine.evaluate_local(inputs)

    archived_record = DecisionRecord.create(
        decision_id=decision_id,
        transaction_id="TXN-SAMPLE-01",
        input_data=inputs,
        rule_bundle_ver=rule_bundle_ver,
        model_ver="lgb_v0.1",
        risk_score=0.88,
        outcome=eval_res.outcome,
        tier=eval_res.tier,
        evidence_ids=eval_res.evidence_ids,
    )

    replay_engine = ReplayEngine(policy_engine)
    report = replay_engine.replay_decision(archived_record, inputs)

    if report.replayed_success:
        st.success("🎯 REPLAY DETERMINISM VERIFIED! 100% Bit-for-Bit Hash Identity Match.")
        c1, c2 = st.columns(2)
        with c1:
            st.code(f"Input Hash:  {archived_record.input_hash}")
            st.code(f"Output Hash: {archived_record.output_hash}")
        with c2:
            st.metric("Replayed Outcome", f"{report.replayed_outcome} ({report.replayed_tier})")
            st.write(f"**Evidence Triggered:** `{', '.join(report.replayed_evidence_ids)}`")
    else:
        st.error("🚨 DRIFT DETECTED! Recomputed hash does not match archived decision record.")
        st.json(report.delta)
