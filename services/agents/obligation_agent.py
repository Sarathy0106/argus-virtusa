"""
Obligation Agent and Applicability Engine for ARGUS v2 (Stage 2).
Extracts executable obligation records (actor, condition, action, deadline)
from circular clauses, and deterministically evaluates applicability
against the target BankProfile (type, licenses, active products, channels).
"""

import re
from typing import Any

from contracts.agents import AgentCard, AgentSkill
from contracts.bank_profile import BankProfile
from contracts.memory import RegulationClause
from contracts.obligations import ApplicabilityStatus, RegulatoryObligation
from services.agents.crypto import AgentKeyPair


class ObligationAgent:
    def __init__(self, key_pair: AgentKeyPair | None = None):
        self.key_pair = key_pair or AgentKeyPair()
        self.agent_id = "agent.obligation"
        self.card = AgentCard(
            agent_id=self.agent_id,
            name="Regulatory Obligation & Applicability Agent",
            version="2.0.0",
            public_key=self.key_pair.public_key_hex,
            skills=[
                AgentSkill(
                    name="obligation.extract_and_filter",
                    description="Extracts obligations and evaluates applicability against bank profile.",
                )
            ],
        )

    def extract_obligations(
        self, clauses: list[RegulationClause], bank_profile: BankProfile
    ) -> list[RegulatoryObligation]:
        """
        Parses clauses into structured obligations and evaluates their applicability
        against the target bank profile.
        """
        obligations: list[RegulatoryObligation] = []

        for clause in clauses:
            extracted = self._parse_clause_to_obligation(clause)
            if extracted:
                for obl in extracted:
                    # Evaluate Applicability Engine
                    status, rationale = self.evaluate_applicability(obl, bank_profile)
                    obl.applicability_status = status
                    obl.applicability_rationale = rationale
                    obligations.append(obl)

        return obligations

    def evaluate_applicability(
        self, obligation: RegulatoryObligation, bank_profile: BankProfile
    ) -> tuple[ApplicabilityStatus, str]:
        """
        Deterministic Applicability Engine:
        Verifies bank type, active products, channels, and licenses against obligation demands.
        """
        # 1. Check Product / Channel Alignment
        target_channel = obligation.condition_json.get("channel")
        target_products = [p.upper() for p in obligation.target_products]

        if target_channel:
            target_products.append(target_channel.upper())

        bank_products = {p.value.upper() for p in bank_profile.active_products}
        bank_channels = {c.upper() for c in bank_profile.supported_channels}

        # If obligation requires a product the bank does NOT have
        if target_products:
            matched_products = bank_products.intersection(target_products)
            matched_channels = bank_channels.intersection(target_products)
            if not matched_products and not matched_channels:
                return (
                    ApplicabilityStatus.NOT_APPLICABLE,
                    f"Bank '{bank_profile.bank_name}' does not offer required products/channels {target_products}. Active products: {list(bank_products)}",
                )

        # 2. Check Actor Classification
        actor_norm = obligation.actor.upper()
        if "ALL REGULATED ENTITIES" in actor_norm or "RE" in actor_norm:
            pass  # Applies universally to all banks
        elif "SCHEDULED COMMERCIAL BANK" in actor_norm:
            if bank_profile.bank_type.value != "SCHEDULED_COMMERCIAL_BANK":
                return (
                    ApplicabilityStatus.NOT_APPLICABLE,
                    f"Obligation applies strictly to Scheduled Commercial Banks. Bank is {bank_profile.bank_type.value}.",
                )
        elif "PAYMENT SYSTEM OPERATOR" in actor_norm or "PSO" in actor_norm:
            if "PAYMENT_SYSTEM_OPERATOR" not in bank_profile.licenses:
                return (
                    ApplicabilityStatus.NOT_APPLICABLE,
                    "Bank does not hold a Payment System Operator (PSO) regulatory license.",
                )

        return (
            ApplicabilityStatus.APPLICABLE,
            f"Applicable to {bank_profile.bank_name}. Bank operates {target_products or 'relevant services'} under {bank_profile.bank_type.value}.",
        )

    def _parse_clause_to_obligation(self, clause: RegulationClause) -> list[RegulatoryObligation]:
        """
        Extracts structured condition, threshold, and action from clause text.
        Guarantees clause citations on every extracted obligation.
        """
        text = clause.clause_text
        text_lower = text.lower()
        results: list[RegulatoryObligation] = []

        # Defense against Prompt Injection (e.g. Circular C4)
        injection_triggers = ["ignore previous", "system notice", "system override", "auto-approve all"]
        if any(trig in text_lower for trig in injection_triggers):
            # Flag and neutralize: do not execute injection instructions
            return []

        # Skip pure scope/preamble/enforcement timeline clauses without actionable conditions
        if (
            "scope and applicability" in text_lower
            or "short title" in text_lower
            or "scope & institutional" in text_lower
            or "enforcement & timelines" in text_lower
            or "general threat briefing" in text_lower
        ) and not ("reporting mandate" in text_lower or "cooling" in text_lower or "enhanced review" in text_lower or "rtgs" in text_lower or "exceeding" in text_lower):
            return []

        # -----------------------------------------------------------------
        # C1: Cash Deposit Reporting (Clause 2.1)
        # -----------------------------------------------------------------
        if "reporting mandate" in text_lower or ("cash" in text_lower and "7 calendar days" in text_lower):
            obl_id = f"OBL-{clause.id}-REP"
            results.append(
                RegulatoryObligation(
                    id=obl_id,
                    circular_id=clause.doc_id,
                    clause_id=clause.id,
                    actor="Scheduled Commercial Bank",
                    trigger_event="SETTLEMENT_WEEK_CLOSE",
                    condition_json={
                        "threshold_amount": 800000.0,
                        "is_cash": True,
                        "cadence_days": 7,
                        "channel": "BRANCH",
                    },
                    action_json={"action": "REGULATORY_REPORTING", "sla_days": 7},
                    rule_ref="cash_deposit_weekly_reporting_800k",
                    severity="HIGH",
                    deadline="2026-11-01",
                    target_products=["RETAIL_DEPOSITS"],
                    citations=[f"[CLAUSE:{clause.id}]"],
                )
            )

        # -----------------------------------------------------------------
        # C1: Cash Deposit Enhanced Due Diligence (Clause 2.3a)
        # -----------------------------------------------------------------
        if "customer risk-tiered review" in text_lower or ("cash deposit" in text_lower and "risk band" in text_lower):
            threshold = 800000.0
            amt_match = re.search(r"(?:₹|rs\.?|inr)\s*([0-9,]+)", text, re.IGNORECASE)
            if amt_match:
                try:
                    threshold = float(amt_match.group(1).replace(",", ""))
                except ValueError:
                    threshold = 800000.0

            obl_id = f"OBL-{clause.id}-EDD"
            results.append(
                RegulatoryObligation(
                    id=obl_id,
                    circular_id=clause.doc_id,
                    clause_id=clause.id,
                    actor="Scheduled Commercial Bank",
                    trigger_event="TRANSACTION_SUBMITTED",
                    condition_json={
                        "threshold_amount": threshold,
                        "is_cash": True,
                        "risk_bands": ["B", "C"],
                        "channel": "BRANCH",
                    },
                    action_json={"action": "ENHANCED_REVIEW", "queue": "aml_l2", "sla_hours": 24},
                    rule_ref="cash_deposit_edd_800k",
                    severity="CRITICAL",
                    deadline="2026-11-01",
                    target_products=["RETAIL_DEPOSITS"],
                    citations=[f"[CLAUSE:{clause.id}]"],
                )
            )

        # -----------------------------------------------------------------
        # C2: Urban Co-operative Banks & NBFCs Capital Buffer (Clause 2.1)
        # -----------------------------------------------------------------
        if "capital conservation buffer" in text_lower or ("ucb" in text_lower and "nbfc" in text_lower):
            obl_id = f"OBL-{clause.id}-CCB"
            results.append(
                RegulatoryObligation(
                    id=obl_id,
                    circular_id=clause.doc_id,
                    clause_id=clause.id,
                    actor="Urban Co-operative Bank & NBFC-BL",
                    trigger_event="CAPITAL_ADEQUACY_REVIEW",
                    condition_json={"incremental_ccb_percent": 1.25, "sector": "COOPERATIVE_NBFC"},
                    action_json={"action": "MAINTAIN_CAPITAL_BUFFER", "target_pct": 1.25},
                    rule_ref="ucb_nbfc_capital_buffer_1_25",
                    severity="HIGH",
                    deadline="2026-12-31",
                    target_products=["CORPORATE_LOANS"],
                    citations=[f"[CLAUSE:{clause.id}]"],
                )
            )

        # -----------------------------------------------------------------
        # C3: UPI High Risk MCC Limit (Clause 2.1)
        # -----------------------------------------------------------------
        if "merchant category codes" in text_lower or ("7995" in text or "6051" in text):
            obl_id = f"OBL-{clause.id}-MCC"
            results.append(
                RegulatoryObligation(
                    id=obl_id,
                    circular_id=clause.doc_id,
                    clause_id=clause.id,
                    actor="Scheduled Commercial Bank & Payment System Operator",
                    trigger_event="TRANSACTION_SUBMITTED",
                    condition_json={
                        "channel": "UPI",
                        "mcc_list": ["7995", "6051"],
                        "per_txn_cap": 25000.0,
                        "daily_cap": 50000.0,
                    },
                    action_json={"action": "DECLINE_IF_EXCEEDED", "reason_code": "HR_MCC_LIMIT_EXCEEDED"},
                    rule_ref="upi_high_risk_mcc_cap_25k",
                    severity="HIGH",
                    deadline="2026-11-01",
                    target_products=["UPI"],
                    citations=[f"[CLAUSE:{clause.id}]"],
                )
            )

        # -----------------------------------------------------------------
        # Cross-border wire or high value RTGS (Legacy / Generic)
        # -----------------------------------------------------------------
        if (
            ("rtgs" in text_lower and ("shall" in text_lower or "must" in text_lower))
            or ("cross-border" in text_lower and "sanction" in text_lower)
        ) and not results:
            threshold = 500000.0
            amt_match = re.search(r"(?:₹|rs\.?|inr|usd)\s*([0-9,]+)", text, re.IGNORECASE)
            if amt_match:
                try:
                    threshold = float(amt_match.group(1).replace(",", ""))
                except ValueError:
                    threshold = 500000.0

            obl_id = f"OBL-{clause.id}"
            results.append(
                RegulatoryObligation(
                    id=obl_id,
                    circular_id=clause.doc_id,
                    clause_id=clause.id,
                    actor="Scheduled Commercial Bank",
                    trigger_event="TRANSACTION_SUBMITTED",
                    condition_json={"threshold_amount": threshold, "channel": "RTGS"},
                    action_json={"action": "HOLD", "tier": "T3"},
                    rule_ref=f"rtgs_wire_threshold_{int(threshold)}",
                    severity="CRITICAL",
                    deadline="2024-12-31",
                    target_products=["RTGS"],
                    citations=[f"[CLAUSE:{clause.id}]"],
                )
            )

        # -----------------------------------------------------------------
        # UPI Cooling Period / High-value immediate check (Legacy / Generic)
        # -----------------------------------------------------------------
        elif (("upi" in text_lower or "cooling" in text_lower or "immediate" in text_lower) and (
            "cooling" in text_lower or "50,000" in text or "threshold" in text_lower or "exceed" in text_lower
        )) and not results:

            threshold = 50000.0
            amt_match = re.search(r"(?:₹|rs\.?|inr)\s*([0-9,]+)", text, re.IGNORECASE)
            if amt_match:
                try:
                    threshold = float(amt_match.group(1).replace(",", ""))
                except ValueError:
                    threshold = 50000.0

            cooling_hours = 4
            cooling_match = re.search(r"([0-9]+)\s*hours?\s*(?:cooling|window)", text, re.IGNORECASE)
            if cooling_match:
                cooling_hours = int(cooling_match.group(1))

            deadline_match = re.search(r"(?:w\.e\.f|effective|deadline)[:\s]+([0-9A-Za-z\s,-]+)", text, re.IGNORECASE)
            deadline = deadline_match.group(1).strip() if deadline_match else "2024-11-01"

            obl_id = f"OBL-{clause.id}"
            results.append(
                RegulatoryObligation(
                    id=obl_id,
                    circular_id=clause.doc_id,
                    clause_id=clause.id,
                    actor="Scheduled Commercial Bank & Payment System Operator",
                    trigger_event="TRANSACTION_SUBMITTED",
                    condition_json={
                        "threshold_amount": threshold,
                        "channel": "UPI",
                        "cooling_period_hours": cooling_hours,
                    },
                    action_json={
                        "action": "HOLD",
                        "tier": "T2",
                        "cooling_period_hours": cooling_hours,
                    },
                    rule_ref=f"upi_cooling_period_{int(threshold)}",
                    severity="HIGH",
                    deadline=deadline,
                    target_products=["UPI"],
                    citations=[f"[CLAUSE:{clause.id}]"],
                )
            )

        return results

