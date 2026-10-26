"""
Deterministic Seed Data for ARGUS Offline Demo Mode.
Provides exactly the spec-mandated sample values with fixed random seed = 42.
"""
import hashlib
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure repo root is importable when used from ui/
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contracts.common import TransactionChannel
from contracts.transactions import Transaction


# ---------------------------------------------------------------------------
# Canonical JSON hashing (matches services/contracts/decisions.py)
# ---------------------------------------------------------------------------
def canonical_json_hash(data: dict) -> str:
    canonical_str = json.dumps(
        data, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Fixed timestamps
# ---------------------------------------------------------------------------
NOW = datetime(2026, 10, 26, 4, 30, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Regulation Clauses
# ---------------------------------------------------------------------------
REGULATION_CLAUSES = [
    {
        "id": "RBI-KYC-C23",
        "doc_id": "RBI-MD-KYC-2016",
        "title": "Periodic Updation of KYC",
        "clause_ref": "Clause-23",
        "clause_text": (
            "Regulated entities shall conduct periodic review and KYC updation every "
            "2 years for high risk customers, 8 years for medium risk, and 10 years "
            "for low risk customers."
        ),
        "valid_from": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "valid_to": datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "keywords": ["kyc", "periodic", "updation", "review", "frequency", "high risk", "medium risk", "low risk", "customer"],
    },
    {
        "id": "RBI-WIRE-C12A",
        "doc_id": "RBI-WIRE-2024",
        "title": "Cross-Border Wire Transfers Reporting",
        "clause_ref": "Clause-12A",
        "clause_text": (
            "All cross-border wire transfers exceeding USD 10,000 or INR 800,000 must "
            "include originator and beneficiary full legal names and account tokens. "
            "Reporting to the regulator is mandatory within 24 hours of execution."
        ),
        "valid_from": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "valid_to": datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "keywords": ["cross-border", "wire", "transfer", "threshold", "reporting", "usd", "inr", "originator", "beneficiary"],
    },
    {
        "id": "RBI-VCIP-C54",
        "doc_id": "RBI-AMEND-2026",
        "title": "Video-based Customer Identification Process (V-CIP)",
        "clause_ref": "Clause-54",
        "clause_text": (
            "Video-based Customer Identification Process (V-CIP) is recognised as "
            "equivalent to physical face-to-face verification, provided geo-tagging "
            "and liveness checks pass and the session is recorded for audit purposes."
        ),
        "valid_from": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "valid_to": datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "keywords": ["vcip", "video", "customer", "identification", "face-to-face", "v-cip", "liveness", "geo"],
    },
    {
        "id": "RBI-AML-C08",
        "doc_id": "RBI-MD-PMLA-2023",
        "title": "Suspicious Transaction Reporting (STR)",
        "clause_ref": "Clause-8",
        "clause_text": (
            "Reporting entities must file a Suspicious Transaction Report (STR) with "
            "the Financial Intelligence Unit (FIU-IND) within 7 days of identifying "
            "a suspicious pattern. The STR must contain account tokens, transaction IDs, "
            "and a structured narrative with evidence citations."
        ),
        "valid_from": datetime(2023, 4, 1, tzinfo=timezone.utc),
        "valid_to": datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "keywords": ["str", "suspicious", "transaction", "report", "fiu", "reporting", "pmla", "narrative", "sar"],
    },
    # This clause expired — useful for time-travel testing
    {
        "id": "RBI-OLD-AML-C04",
        "doc_id": "RBI-MD-AML-2015",
        "title": "Legacy Cash Transaction Reporting (CTR)",
        "clause_ref": "Clause-4",
        "clause_text": (
            "[EXPIRED RULE] Cash transactions above INR 1,00,000 must be reported monthly. "
            "Superseded by RBI-MD-PMLA-2023 Clause-8."
        ),
        "valid_from": datetime(2015, 1, 1, tzinfo=timezone.utc),
        "valid_to": datetime(2023, 3, 31, tzinfo=timezone.utc),
        "keywords": ["cash", "ctr", "legacy", "old", "monthly"],
    },
]


# ---------------------------------------------------------------------------
# SHAP Attribution Table
# ---------------------------------------------------------------------------
SHAP_ROWS_MULE = [
    {
        "Feature": "rapid_pass_through_delta",
        "Attribution": "+0.45",
        "Value": "+0.45",
        "Description": "Funds dispersed in < 15 mins after inflow",
    },
    {
        "Feature": "shared_device_account_count",
        "Attribution": "+0.32",
        "Value": "+0.32",
        "Description": "Same device fingerprint across 4 accounts",
    },
    {
        "Feature": "structuring_window_count_24h",
        "Attribution": "+0.28",
        "Value": "+0.28",
        "Description": "Multiple transfers near INR 50k threshold",
    },
    {
        "Feature": "counterparty_graph_hops",
        "Attribution": "+0.19",
        "Value": "+0.19",
        "Description": "3 hop distance to known flagged entity",
    },
    {
        "Feature": "account_age_days",
        "Attribution": "-0.08",
        "Value": "-0.08",
        "Description": "Account older than 180 days (lower risk)",
    },
]

SHAP_ROWS_STRUC = [
    {
        "Feature": "structuring_window_count_24h",
        "Attribution": "+0.51",
        "Value": "+0.51",
        "Description": "5 transfers between INR 49k–50k within 24h",
    },
    {
        "Feature": "amount_below_threshold_margin",
        "Attribution": "+0.33",
        "Value": "+0.33",
        "Description": "All amounts within 3% of reporting threshold",
    },
    {
        "Feature": "velocity_count_24h",
        "Attribution": "+0.22",
        "Value": "+0.22",
        "Description": "18 transactions in 24-hour window",
    },
    {
        "Feature": "account_age_days",
        "Attribution": "-0.11",
        "Value": "-0.11",
        "Description": "Account older than 365 days (lower risk)",
    },
]


# ---------------------------------------------------------------------------
# Deterministic Case Data
# ---------------------------------------------------------------------------
def build_seed_cases():
    """Returns the two spec-mandated cases with fixed IDs and amounts."""
    cases = [
        {
            "case_id": "CASE-MULE-8821",
            "title": "Suspected Mule Dispersal Ring (4 txns, INR 900,000.00)",
            "primary_tier": "T2",
            "transaction_ids": ["TXN-MULE-901", "TXN-DISPERSAL-1", "TXN-DISPERSAL-2", "TXN-DISPERSAL-3"],
            "total_amount": 900000.0,
            "linked_accounts": [
                "<ACCT_CASH_OUT_1>",
                "<ACCT_CASH_OUT_2>",
                "<ACCT_CASH_OUT_3>",
                "<ACCT_CRIME_ORIGIN>",
                "<ACCT_MULE_HUB_01>",
            ],
            "linked_devices": ["<DEV_MULE_RING_A>"],
            "evidence_types": ["rapid_pass_through", "shared_device_ring"],
            "shap_rows": SHAP_ROWS_MULE,
            "case_graph": {
                "node_count": 10,
                "edge_count": 12,
                "nodes": [
                    {"id": "TXN_TXN-MULE-901",     "type": "TRANSACTION"},
                    {"id": "TXN_TXN-DISPERSAL-1",  "type": "TRANSACTION"},
                    {"id": "TXN_TXN-DISPERSAL-2",  "type": "TRANSACTION"},
                    {"id": "TXN_TXN-DISPERSAL-3",  "type": "TRANSACTION"},
                    {"id": "ACCT_<ACCT_CRIME_ORIGIN>", "type": "ACCOUNT"},
                    {"id": "ACCT_<ACCT_MULE_HUB_01>",  "type": "COUNTERPARTY"},
                    {"id": "ACCT_<ACCT_CASH_OUT_1>",    "type": "COUNTERPARTY"},
                    {"id": "ACCT_<ACCT_CASH_OUT_2>",    "type": "COUNTERPARTY"},
                    {"id": "ACCT_<ACCT_CASH_OUT_3>",    "type": "COUNTERPARTY"},
                    {"id": "DEV_<DEV_MULE_RING_A>",     "type": "DEVICE"},
                ],
                "edges": [
                    {"source": "TXN_TXN-MULE-901",    "target": "ACCT_<ACCT_CRIME_ORIGIN>",  "relation": "ORIGIN"},
                    {"source": "TXN_TXN-MULE-901",    "target": "ACCT_<ACCT_MULE_HUB_01>",   "relation": "DESTINATION"},
                    {"source": "TXN_TXN-MULE-901",    "target": "DEV_<DEV_MULE_RING_A>",     "relation": "DEVICE_USED"},
                    {"source": "TXN_TXN-DISPERSAL-1", "target": "ACCT_<ACCT_MULE_HUB_01>",   "relation": "ORIGIN"},
                    {"source": "TXN_TXN-DISPERSAL-1", "target": "ACCT_<ACCT_CASH_OUT_1>",    "relation": "DESTINATION"},
                    {"source": "TXN_TXN-DISPERSAL-1", "target": "DEV_<DEV_MULE_RING_A>",     "relation": "DEVICE_USED"},
                    {"source": "TXN_TXN-DISPERSAL-2", "target": "ACCT_<ACCT_MULE_HUB_01>",   "relation": "ORIGIN"},
                    {"source": "TXN_TXN-DISPERSAL-2", "target": "ACCT_<ACCT_CASH_OUT_2>",    "relation": "DESTINATION"},
                    {"source": "TXN_TXN-DISPERSAL-2", "target": "DEV_<DEV_MULE_RING_A>",     "relation": "DEVICE_USED"},
                    {"source": "TXN_TXN-DISPERSAL-3", "target": "ACCT_<ACCT_MULE_HUB_01>",   "relation": "ORIGIN"},
                    {"source": "TXN_TXN-DISPERSAL-3", "target": "ACCT_<ACCT_CASH_OUT_3>",    "relation": "DESTINATION"},
                    {"source": "TXN_TXN-DISPERSAL-3", "target": "DEV_<DEV_MULE_RING_A>",     "relation": "DEVICE_USED"},
                ],
            },
        },
        {
            "case_id": "CASE-STRUC-1049",
            "title": "Structuring Window Pattern across 2 counterparties",
            "primary_tier": "T1",
            "transaction_ids": ["TXN-STRUC-880", "TXN-STRUC-881", "TXN-STRUC-882", "TXN-STRUC-883"],
            "total_amount": 197700.0,
            "linked_accounts": ["<ACCT_BENEFICIARY_B>", "<ACCT_SMURF_A>"],
            "linked_devices": ["<DEV_SMURF_01>"],
            "evidence_types": ["aml_structuring_window"],
            "shap_rows": SHAP_ROWS_STRUC,
            "case_graph": {
                "node_count": 7,
                "edge_count": 8,
                "nodes": [
                    {"id": "TXN_TXN-STRUC-880", "type": "TRANSACTION"},
                    {"id": "TXN_TXN-STRUC-881", "type": "TRANSACTION"},
                    {"id": "TXN_TXN-STRUC-882", "type": "TRANSACTION"},
                    {"id": "TXN_TXN-STRUC-883", "type": "TRANSACTION"},
                    {"id": "ACCT_<ACCT_SMURF_A>",       "type": "ACCOUNT"},
                    {"id": "ACCT_<ACCT_BENEFICIARY_B>",  "type": "COUNTERPARTY"},
                    {"id": "DEV_<DEV_SMURF_01>",         "type": "DEVICE"},
                ],
                "edges": [
                    {"source": "TXN_TXN-STRUC-880", "target": "ACCT_<ACCT_SMURF_A>",      "relation": "ORIGIN"},
                    {"source": "TXN_TXN-STRUC-880", "target": "ACCT_<ACCT_BENEFICIARY_B>", "relation": "DESTINATION"},
                    {"source": "TXN_TXN-STRUC-881", "target": "ACCT_<ACCT_SMURF_A>",      "relation": "ORIGIN"},
                    {"source": "TXN_TXN-STRUC-881", "target": "ACCT_<ACCT_BENEFICIARY_B>", "relation": "DESTINATION"},
                    {"source": "TXN_TXN-STRUC-882", "target": "ACCT_<ACCT_SMURF_A>",      "relation": "ORIGIN"},
                    {"source": "TXN_TXN-STRUC-882", "target": "ACCT_<ACCT_BENEFICIARY_B>", "relation": "DESTINATION"},
                    {"source": "TXN_TXN-STRUC-883", "target": "ACCT_<ACCT_SMURF_A>",      "relation": "ORIGIN"},
                    {"source": "TXN_TXN-STRUC-883", "target": "ACCT_<ACCT_BENEFICIARY_B>", "relation": "DESTINATION"},
                ],
            },
        },
    ]
    return cases


# ---------------------------------------------------------------------------
# Seed Audit Ledger
# ---------------------------------------------------------------------------
GENESIS_HASH = "0" * 64


def _compute_block_hash(prev_hash: str, payload: dict, event_type: str,
                         entity_id: str, signer: str, recorded_at: str) -> str:
    payload_hash = canonical_json_hash(payload)
    chain_input = f"{prev_hash}{payload_hash}{event_type}{entity_id}{signer}{recorded_at}"
    return hashlib.sha256(chain_input.encode("utf-8")).hexdigest()


def build_seed_ledger():
    blocks = []
    prev = GENESIS_HASH

    entries = [
        {
            "event_type": "SYSTEM_GENESIS",
            "entity_id": "SYS-001",
            "signer": "system_vault",
            "payload": {"version": "1.0.0", "status": "INITIALIZED", "bundle": "argus-policies-v1.0.0"},
            "recorded_at": "2026-10-26T00:00:00+00:00",
        },
        {
            "event_type": "DECISION_RECORDED",
            "entity_id": "DEC-1001",
            "signer": "agent.txn_risk",
            "payload": {"transaction_id": "TXN-881", "outcome": "HOLD", "tier": "T1",
                        "rule_bundle_ver": "1.0.0", "risk_score": 0.74},
            "recorded_at": "2026-10-26T01:12:44+00:00",
        },
        {
            "event_type": "CASE_RESOLVED_CONFIRMED",
            "entity_id": "CASE-MULE-8821",
            "signer": "maker:analyst_alice|checker:compliance_head_david",
            "payload": {"verdict": "CONFIRMED_SUSPICIOUS", "tier": "T2",
                        "total_amount": 900000.0, "str_filed": True},
            "recorded_at": "2026-10-26T02:30:11+00:00",
        },
        {
            "event_type": "RULE_BUNDLE_PUBLISHED",
            "entity_id": "POL-WIRE-01",
            "signer": "maker:compliance_officer_sarah|checker:risk_head_marcus",
            "payload": {"rule": "cross_border_wire", "bundle_version": "1.1.0",
                        "obligation_id": "OBL-RBI-WIRE-2026-01"},
            "recorded_at": "2026-10-26T03:45:00+00:00",
        },
    ]

    for i, e in enumerate(entries):
        block_hash = _compute_block_hash(
            prev, e["payload"], e["event_type"], e["entity_id"], e["signer"], e["recorded_at"]
        )
        blocks.append({
            "seq": i + 1,
            "prev_hash": prev,
            "block_hash": block_hash,
            "event_type": e["event_type"],
            "entity_id": e["entity_id"],
            "signer": e["signer"],
            "payload": e["payload"],
            "recorded_at": e["recorded_at"],
        })
        prev = block_hash

    return blocks


# ---------------------------------------------------------------------------
# 150 Synthetic Transactions (deterministic seed=42)
# ---------------------------------------------------------------------------
def build_seed_transactions(n: int = 150) -> list[dict]:
    rng = random.Random(42)
    accounts = [f"<ACCT_{rng.randint(1000, 9999):X}>" for _ in range(20)]
    devices = [f"<DEV_{rng.randint(1000, 9999):X}>" for _ in range(10)]
    channels = ["UPI", "NEFT", "RTGS", "IMPS"]
    txns = []
    base_ts = datetime(2026, 10, 1, tzinfo=timezone.utc)

    for i in range(n):
        ts = base_ts + timedelta(hours=rng.randint(0, 600))
        origin = rng.choice(accounts)
        dest = rng.choice([a for a in accounts if a != origin])
        amount = round(rng.uniform(1000, 950000), 2)
        channel = rng.choice(channels)
        txns.append({
            "id": f"TXN-HIST-{i+1:04d}",
            "account_token": origin,
            "counterparty_token": dest,
            "amount": amount,
            "currency": "INR",
            "timestamp": ts.isoformat(),
            "channel": channel,
            "device_id_token": rng.choice(devices),
            "location_country": "IND",
        })
    return txns


# Singletons built at import time (fast, deterministic)
SEED_CASES = build_seed_cases()
SEED_LEDGER = build_seed_ledger()
SEED_TRANSACTIONS = build_seed_transactions(150)
