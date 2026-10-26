"""
Deterministic Seed Data for ARGUS v2 — Circular to Live Rule Engine.
Contains Bank Profiles, Circular Documents with Clauses, Internal Policies,
Existing Rules, Historical Transactions, and complete Traceability Graph.
"""
from datetime import datetime, timezone
import hashlib
import json

# ---------------------------------------------------------------------------
# Bank Profiles
# ---------------------------------------------------------------------------
BANK_PROFILES = [
    {
        "id": "BANK-APEX-01",
        "name": "Apex Global Commercial Bank Ltd.",
        "short_name": "Apex Commercial Bank",
        "license_type": "SCHEDULED_COMMERCIAL_BANK",
        "has_ad_cat1_forex": True,
        "licensed_products": ["UPI", "RTGS", "NEFT", "CROSS_BORDER_WIRE", "CREDIT_CARDS", "FOREX", "DIGITAL_LENDING"],
        "jurisdictions": ["IN", "GLOBAL"],
        "tier": "TIER_1_DSIB",
        "badge": "Scheduled Commercial Bank · AD Cat-1 Forex",
    },
    {
        "id": "BANK-FINZAP-02",
        "name": "FinZap Payments Bank Ltd.",
        "short_name": "FinZap Payments Bank",
        "license_type": "PAYMENT_BANK",
        "has_ad_cat1_forex": False,
        "licensed_products": ["UPI", "IMPS", "BILL_PAYMENTS", "WALLET", "DOMESTIC_REMITTANCE"],
        "jurisdictions": ["IN"],
        "tier": "TIER_3_PAYMENT_BANK",
        "badge": "Payments Bank · No Cross-Border Wire License",
    },
]

# ---------------------------------------------------------------------------
# Regulatory Circulars & Clauses
# ---------------------------------------------------------------------------
CIRCULARS = [
    {
        "id": "RBI/2026/04/MD-WIRE",
        "title": "RBI Master Direction on Cross-Border Wire Transfers & Travel Rule Mandate (2026)",
        "authority": "Reserve Bank of India (RBI)",
        "circular_ref": "RBI/DOR/2026-27/104",
        "published_date": "2026-01-15T00:00:00Z",
        "effective_date": "2026-04-01T00:00:00Z",
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_to": "2029-12-31T23:59:59Z",
        "status": "IN_FORCE",
        "summary": "Mandates automated screening, full originator/beneficiary identification, and real-time AML holds on outward cross-border wires exceeding USD 10,000 or INR 800,000.",
        "clauses": [
            {
                "id": "RBI-WIRE-C12A",
                "clause_ref": "Section 12, Subsection (a)",
                "title": "Outward Cross-Border Wire Threshold & Full Identification",
                "clause_text": (
                    "All cross-border wire transfers exceeding USD 10,000 or INR 800,000 equivalent must include "
                    "originator full legal name, account token, national identifier, and beneficiary verified details. "
                    "Regulated entities shall hold and inspect transactions exceeding this threshold prior to international dispatch."
                ),
                "actor": "Authorized Dealer Category-I Banks, Commercial Banks",
                "trigger_event": "TRANSACTION_SUBMITTED",
                "threshold_amount": 800000.0,
                "channel": "RTGS",
                "currency": "INR",
                "action": "HOLD",
                "tier": "T2",
                "keywords": ["wire", "cross-border", "swift", "rtgs", "threshold", "travel rule", "outward"],
            },
            {
                "id": "RBI-WIRE-C12B",
                "clause_ref": "Section 12, Subsection (b)",
                "title": "Real-time Sanctions Screening & LEI Verification",
                "clause_text": (
                    "All outward corporate wire remittances exceeding INR 5,000,000 must verify the active Legal Entity Identifier (LEI) "
                    "of both counterparty entities against the global GLEIF database in real time before message generation."
                ),
                "actor": "Commercial Banks with Corporate Remittance Desks",
                "trigger_event": "CORPORATE_WIRE_SUBMITTED",
                "threshold_amount": 5000000.0,
                "channel": "RTGS",
                "currency": "INR",
                "action": "ESCALATE",
                "tier": "T2",
                "keywords": ["lei", "gleif", "corporate", "wire", "sanctions", "screening"],
            },
        ],
    },
    {
        "id": "RBI/2026/01/MD-KYC",
        "title": "RBI Master Direction — Know Your Customer (KYC) Direction, Amendment 2026",
        "authority": "Reserve Bank of India (RBI)",
        "circular_ref": "RBI/DBR/2026-27/12",
        "published_date": "2026-01-05T00:00:00Z",
        "effective_date": "2026-02-01T00:00:00Z",
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_to": "2030-12-31T23:59:59Z",
        "status": "IN_FORCE",
        "summary": "Mandates high-risk customer re-KYC at least once every 2 years, medium-risk every 8 years, and low-risk every 10 years.",
        "clauses": [
            {
                "id": "RBI-KYC-C04",
                "clause_ref": "Chapter VI, Section 38",
                "title": "Periodic Updation of KYC for High-Risk Categories",
                "clause_text": (
                    "Regulated entities shall carry out periodic KYC updation at least once every two years for high-risk customers, "
                    "once every eight years for medium-risk customers, and once every ten years for low-risk customers."
                ),
                "actor": "All Regulated Entities, Commercial Banks, NBFCs, Payment Banks",
                "trigger_event": "KYC_PERIODIC_REVIEW",
                "threshold_amount": 0.0,
                "channel": "ALL",
                "currency": "INR",
                "action": "FLAG_FOR_REVIEW",
                "tier": "T1",
                "keywords": ["kyc", "periodic", "updation", "high risk", "pep"],
            }
        ],
    },
    {
        "id": "RBI/2022/11/CTR-LEGACY",
        "title": "RBI Cash Transaction Monthly Reporting (CTR-M) — Legacy Framework",
        "authority": "Reserve Bank of India (RBI)",
        "circular_ref": "RBI/2022-23/88 (Superseded)",
        "published_date": "2022-11-01T00:00:00Z",
        "effective_date": "2022-11-15T00:00:00Z",
        "valid_from": "2022-11-01T00:00:00Z",
        "valid_to": "2023-03-31T23:59:59Z",
        "status": "EXPIRED",
        "summary": "Superseded monthly cash reporting rule — system must strictly abstain when evaluated on current dates.",
        "clauses": [
            {
                "id": "RBI-CTR-LEGACY-01",
                "clause_ref": "Schedule IV, Item 2",
                "title": "Legacy Monthly Cash Aggregation Reporting",
                "clause_text": "All cash deposits exceeding INR 1,000,000 aggregated monthly required manual offline CTR-M return filing.",
                "actor": "Commercial Banks",
                "trigger_event": "MONTHLY_CASH_AGGREGATE",
                "threshold_amount": 1000000.0,
                "channel": "CASH",
                "currency": "INR",
                "action": "FILE_CTR_M",
                "tier": "T0",
                "keywords": ["legacy", "ctr", "old", "monthly", "expired"],
            }
        ],
    },
]

# ---------------------------------------------------------------------------
# Internal Bank Policies & Traceability
# ---------------------------------------------------------------------------
INTERNAL_POLICIES = [
    {
        "policy_id": "POL-WIRE-INTL-01",
        "title": "Group International Funds Transfer & Cross-Border Remittance Policy",
        "version": "3.2.0",
        "owner": "Head of Global Compliance",
        "current_threshold_inr": 1000000.0,  # Note: currently 1,000,000, while new circular is 800,000! (GAP)
        "current_rule_ref": "rule_intl_wire_v1",
        "description": "Governs outward cross-border wire processing, screening and reporting thresholds.",
    },
    {
        "policy_id": "POL-LIMITS-RETAIL-04",
        "title": "Retail Daily Velocity & Outward Transfer Limit Standards",
        "version": "2.1.0",
        "owner": "Head of Retail Risk",
        "current_threshold_inr": 500000.0,  # Retail policy imposes a hard internal ceiling at 500,000! (CONFLICT)
        "current_rule_ref": "rule_retail_daily_limit",
        "description": "Sets daily operational limits per retail customer segment.",
    },
    {
        "policy_id": "POL-KYC-REAUTH-02",
        "title": "Customer Due Diligence & High-Risk Periodic KYC Standard",
        "version": "4.0.0",
        "owner": "Chief Anti-Money Laundering Officer (CAMLO)",
        "current_threshold_inr": 0.0,
        "current_rule_ref": "rule_kyc_high_risk_2yr",
        "description": "Enforces 2-year refresh on PEPs and high-risk accounts.",
    },
]

# ---------------------------------------------------------------------------
# Existing Live Rule Repository (in Core OPA)
# ---------------------------------------------------------------------------
EXISTING_RULES = [
    {
        "rule_id": "RULE-LEGACY-WIRE-01",
        "name": "rule_intl_wire_v1",
        "channel": "RTGS",
        "threshold": 1000000.0,
        "action": "HOLD",
        "tier": "T2",
        "deployed_version": "v1.0.0",
        "last_updated": "2024-06-15T10:00:00Z",
        "status": "LIVE_ENFORCING",
    },
    {
        "rule_id": "RULE-RETAIL-CEILING-02",
        "name": "rule_retail_daily_limit",
        "channel": "ALL",
        "threshold": 500000.0,
        "action": "BLOCK",
        "tier": "T1",
        "deployed_version": "v1.0.0",
        "last_updated": "2024-03-10T12:00:00Z",
        "status": "LIVE_ENFORCING",
    },
    {
        "rule_id": "RULE-KYC-HIGH-RISK",
        "name": "rule_kyc_high_risk_2yr",
        "channel": "ALL",
        "threshold": 0.0,
        "action": "FLAG_FOR_REVIEW",
        "tier": "T1",
        "deployed_version": "v1.0.0",
        "last_updated": "2025-01-10T09:00:00Z",
        "status": "LIVE_ENFORCING",
    },
]

# ---------------------------------------------------------------------------
# Pre-computed V2 10-Stage Pipeline State (for Instant Demo & Interactive Walkthrough)
# ---------------------------------------------------------------------------
SAMPLE_PIPELINE_CASE = {
    "circular_id": "RBI/2026/04/MD-WIRE",
    "clause_id": "RBI-WIRE-C12A",
    "obligation": {
        "id": "OBL-RBI-WIRE-2026-01",
        "clause_id": "RBI-WIRE-C12A",
        "actor": "Authorized Dealer Category-I Banks, Commercial Banks",
        "trigger_event": "TRANSACTION_SUBMITTED",
        "condition_json": {
            "threshold_amount": 800000.0,
            "channel": "RTGS",
            "currency": "INR",
            "transaction_type": "CROSS_BORDER_WIRE",
        },
        "action_json": {
            "action": "HOLD",
            "tier": "T2",
            "notify": "compliance_officer",
        },
        "rule_ref": "cross_border_wire_threshold",
        "severity": "CRITICAL",
        "statutory_deadline": "2026-04-01",
    },
    "policy_mapping": [
        {
            "obligation_id": "OBL-RBI-WIRE-2026-01",
            "clause_ref": "RBI-WIRE-C12A",
            "internal_policy_id": "POL-WIRE-INTL-01",
            "internal_policy_title": "Group International Funds Transfer Policy",
            "existing_rule_ref": "rule_intl_wire_v1",
            "existing_threshold": 1000000.0,
            "proposed_threshold": 800000.0,
            "mapping_type": "GAP",
            "conflict_detail": "Bank's existing threshold is ₹1,000,000; statutory circular mandates tighter ₹800,000 limit. Gap of ₹200,000 unmonitored.",
            "suggested_action": "Tighten threshold from ₹1,000,000 to ₹800,000 in rule_intl_wire.",
        },
        {
            "obligation_id": "OBL-RBI-WIRE-2026-01",
            "clause_ref": "RBI-WIRE-C12A",
            "internal_policy_id": "POL-LIMITS-RETAIL-04",
            "internal_policy_title": "Retail Daily Velocity Limit Standards",
            "existing_rule_ref": "rule_retail_daily_limit",
            "existing_threshold": 500000.0,
            "proposed_threshold": 800000.0,
            "mapping_type": "CONFLICT",
            "conflict_detail": "Retail policy enforces hard block at ₹500,000. An unconditioned ₹800,000 rule would conflict with the existing retail limit without account segment scoping.",
            "suggested_action": "Scope candidate rule to apply explicitly to Corporate & AD-Cat 1 International Remittances, exempting retail daily ceiling.",
        },
    ],
    "rule_dsl_yaml": """# ARGUS Rule DSL — YAML Specification (v1.1.0)
rule_spec:
  rule_id: "RULE-2026-WIRE-C12A"
  name: "cross_border_wire_threshold"
  version: "1.1.0"
  status: "DRAFT_ONLY"
  traceability:
    source_clause: "RBI-WIRE-C12A"
    obligation_id: "OBL-RBI-WIRE-2026-01"
    circular: "RBI/2026/04/MD-WIRE"
    statutory_deadline: "2026-04-01"
  conditions:
    channel: "RTGS"
    currency: "INR"
    amount_gte: 800000.0
    account_category: ["CORPORATE", "AD_CAT1_REMITTANCE"]
  actions:
    outcome: "HOLD"
    governance_tier: "T2"
    evidence_id: "RBI_WIRE_TRAVEL_RULE_C12A"
    require_maker_checker: true
""",
    "compiled_rego": """package argus.compiled.cross_border_wire_threshold

# Auto-compiled from Obligation: OBL-RBI-WIRE-2026-01 (Clause: RBI-WIRE-C12A)
# Target Engine: Open Policy Agent v0.68.0
# Lifecycle State: DRAFT (Non-enforcing)
default rule_hit := false

rule_hit if {
    input.amount >= 800000.0
    input.channel == "RTGS"
    input.currency == "INR"
}

decision := {
    "outcome": "HOLD",
    "tier": "T2",
    "evidence_id": "cross_border_wire_threshold",
    "statutory_ref": "RBI-WIRE-C12A",
    "requires_dual_signoff": true
} if rule_hit
""",
    "compiled_rego_tests": """package argus.compiled.cross_border_wire_threshold_test

import data.argus.compiled.cross_border_wire_threshold

test_wire_above_threshold_triggers_hold if {
    rule_hit with input as {
        "amount": 850000.0,
        "channel": "RTGS",
        "currency": "INR"
    }
}

test_wire_below_threshold_passes if {
    not rule_hit with input as {
        "amount": 799000.0,
        "channel": "RTGS",
        "currency": "INR"
    }
}

test_different_channel_ignored if {
    not rule_hit with input as {
        "amount": 950000.0,
        "channel": "UPI",
        "currency": "INR"
    }
}
""",
    "backtest_report": {
        "rule_id": "RULE-2026-WIRE-C12A",
        "baseline_rule_id": "RULE-LEGACY-WIRE-01 (v1.0.0)",
        "total_transactions_analyzed": 150,
        "baseline_alert_count": 12,
        "candidate_alert_count": 28,
        "alert_increase_count": 16,
        "delta_percentage": 133.3,
        "total_flagged_volume_inr": 34850000.0,
        "estimated_ops_hours_per_month": 14.5,
        "false_positive_estimate_pct": 3.8,
        "sandbox_run_id": "SANDBOX-RUN-88392",
        "affected_customer_segments": [
            {"segment": "Corporate Importers & Global Trade", "share_pct": 68.0, "volume_inr": 23700000.0},
            {"segment": "NRI High-Value Inward/Outward", "share_pct": 22.0, "volume_inr": 7667000.0},
            {"segment": "SME Cross-Border SaaS/Services", "share_pct": 10.0, "volume_inr": 3483000.0},
        ],
    },
    "validation_history": [
        {
            "iteration": 1,
            "passed": False,
            "schema_ok": True,
            "coverage_ok": True,
            "citation_grounded": True,
            "no_conflict_ok": False,
            "objections": [
                "CONFLICT OBJECTION: Candidate rule lacks explicit account scoping, causing conflict with existing Retail Velocity Ceiling (POL-LIMITS-RETAIL-04 at ₹500,000).",
                "RE-ROUTE: Routing draft back to Policy Mapper and Rule Author to inject explicit account_category: ['CORPORATE', 'AD_CAT1'] constraint."
            ],
            "re_route_stage": "STAGE_4_RULE_AUTHORING",
        },
        {
            "iteration": 2,
            "passed": True,
            "schema_ok": True,
            "coverage_ok": True,
            "citation_grounded": True,
            "no_conflict_ok": True,
            "objections": [],
            "re_route_stage": None,
        },
    ],
    "approvals": {
        "maker": "sarah_compliance_lead",
        "maker_role": "AVP Regulatory Compliance",
        "maker_timestamp": "2026-03-20T11:15:00Z",
        "checker": "marcus_risk_head",
        "checker_role": "Chief Risk Officer (CRO)",
        "checker_timestamp": "2026-03-20T14:40:00Z",
        "approval_status": "APPROVED",
        "ed25519_signature": "ed25519_sig_9f83ac8b22e19d77e44b8100ef3199bc4512eac1048",
        "audit_block_seq": 5,
        "ledger_hash": "c8f2a1b9d4e5f7a23c4d8e9f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
    },
    "rollout": {
        "rule_id": "RULE-2026-WIRE-C12A",
        "current_state": "CANARY_10",
        "canary_percentage": 10,
        "shadow_events_count": 4820,
        "divergence_count": 18,
        "divergence_rate_pct": 0.37,
        "p95_eval_latency_ms": 3.8,
        "auto_rollback_threshold_divergence_pct": 5.0,
        "is_rolled_back": False,
        "previous_bundle_tag": "v1.0.0",
        "candidate_bundle_tag": "v1.1.0-canary",
    },
}
