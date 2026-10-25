"""
Stateful Investigation Orchestrator for ARGUS.
Coordinates:
Transaction Ingest -> PII Airlock -> Risk Agent -> Investigator -> Narrative Agent
-> HITL Interrupts (T1 Analyst, T2 Maker-Checker, T3 Compliance Signoff) -> Hash-Chained Audit Ledger.
"""

from typing import Any

from pydantic import BaseModel, Field

from contracts.common import DecisionOutcome, RiskTier
from contracts.decisions import DecisionRecord
from contracts.transactions import Transaction
from services.agents.investigator import InvestigatorAgent
from services.agents.kyc_sanctions import KYCSanctionsAgent
from services.agents.narrative import NarrativeAgent
from services.agents.txn_risk import TxnRiskAgent
from services.airlock.airlock import PIIAirlock
from services.ledger.ledger import AuditLedger
from services.memory.bitemporal import BitemporalMemoryStore
from services.memory.feedback import FeedbackLoopManager


class OrchestrationState(BaseModel):
    transaction: Transaction
    tokenized_txn: Transaction | None = None
    risk_evaluation: dict[str, Any] = Field(default_factory=dict)
    sanctions_check: dict[str, Any] = Field(default_factory=dict)
    dossier: dict[str, Any] = Field(default_factory=dict)
    narrative: dict[str, Any] = Field(default_factory=dict)
    decision_record: DecisionRecord | None = None
    hitl_required: bool = False
    hitl_tier: RiskTier = RiskTier.T0
    hitl_status: str = "PENDING"  # PENDING, APPROVED, REJECTED, AUTO_PASSED
    maker: str | None = None
    checker: str | None = None
    audit_hash: str | None = None


class ArgusOrchestrator:
    def __init__(
        self,
        airlock: PIIAirlock | None = None,
        txn_risk_agent: TxnRiskAgent | None = None,
        kyc_agent: KYCSanctionsAgent | None = None,
        investigator: InvestigatorAgent | None = None,
        narrative_agent: NarrativeAgent | None = None,
        memory_store: BitemporalMemoryStore | None = None,
        audit_ledger: AuditLedger | None = None,
        feedback_loop: FeedbackLoopManager | None = None,
    ):
        self.airlock = airlock or PIIAirlock()
        self.txn_risk_agent = txn_risk_agent or TxnRiskAgent()
        self.kyc_agent = kyc_agent or KYCSanctionsAgent()
        self.investigator = investigator or InvestigatorAgent()
        self.narrative_agent = narrative_agent or NarrativeAgent()
        self.memory = memory_store or BitemporalMemoryStore()
        self.audit_ledger = audit_ledger or AuditLedger()
        self.feedback_loop = feedback_loop or FeedbackLoopManager()

    def process_transaction(self, raw_txn: Transaction) -> OrchestrationState:
        """
        Runs automated pipeline until auto-completion (T0) or HITL interrupt point (T1/T2/T3).
        """
        # Step 1: PII Airlock Tokenization of Transaction narrative/data
        tokenized_narrative = self.airlock.tokenize_text(raw_txn.narrative or "", scope=raw_txn.id)
        tokenized_txn = raw_txn.model_copy(update={"narrative": tokenized_narrative})

        # Step 2: Sanctions Pre-check via KYC Agent
        sanctions_res = self.kyc_agent.verify_account(
            account_token=tokenized_txn.account_token,
            counterparty_token=tokenized_txn.counterparty_token,
        )

        # Step 3: Risk Evaluation via Txn Risk Agent
        risk_res = self.txn_risk_agent.evaluate_transaction(tokenized_txn)

        # Sanctions override if match found
        if sanctions_res.get("sanctions_hit"):
            risk_res["outcome"] = "BLOCK"
            risk_res["tier"] = "T3"
            risk_res["evidence_ids"].append("sanctions_exact_match")

        tier = RiskTier(risk_res["tier"])
        outcome = DecisionOutcome(risk_res["outcome"])

        # Construct initial Decision Record
        input_payload = {
            "amount": tokenized_txn.amount,
            "account_token": tokenized_txn.account_token,
            "counterparty_token": tokenized_txn.counterparty_token,
            "channel": tokenized_txn.channel.value,
            "location_country": tokenized_txn.location_country,
            "sanctions_hit": sanctions_res.get("sanctions_hit", False),
        }

        decision_rec = DecisionRecord.create(
            decision_id=f"DEC-{tokenized_txn.id}",
            transaction_id=tokenized_txn.id,
            input_data=input_payload,
            rule_bundle_ver=risk_res.get("rule_bundle_ver", "1.0.0"),
            model_ver=risk_res.get("model_ver", "lgb_v0.1"),
            risk_score=risk_res.get("risk_score", 0.0),
            outcome=outcome,
            tier=tier,
            evidence_ids=risk_res.get("evidence_ids", []),
        )

        # Step 4: Branching based on Human-in-the-Loop Tier
        state = OrchestrationState(
            transaction=raw_txn,
            tokenized_txn=tokenized_txn,
            risk_evaluation=risk_res,
            sanctions_check=sanctions_res,
            decision_record=decision_rec,
            hitl_tier=tier,
        )

        if tier == RiskTier.T0 and outcome == DecisionOutcome.ALLOW:
            # Fully automated pass: append directly to audit ledger
            audit_entry = self.audit_ledger.append(
                event_type="DECISION_AUTOMATED_ALLOW",
                entity_id=decision_rec.id,
                signer="orchestrator.auto",
                payload=decision_rec.model_dump(mode="json"),
            )
            state.hitl_required = False
            state.hitl_status = "AUTO_PASSED"
            state.audit_hash = audit_entry.verify_hash()
            return state

        # Step 5: For T1, T2, T3, trigger Investigator & Narrative Agents
        dossier = self.investigator.assemble_dossier(tokenized_txn, risk_res)
        narrative_res = self.narrative_agent.draft_narrative(dossier)

        state.dossier = dossier
        state.narrative = narrative_res
        state.hitl_required = True
        state.hitl_status = "PENDING"
        return state

    def resolve_hitl_checkpoint(
        self,
        state: OrchestrationState,
        analyst_verdict: str,  # APPROVED, REJECTED, FALSE_POSITIVE
        maker_id: str,
        checker_id: str | None = None,
        analyst_notes: str = "",
    ) -> OrchestrationState:
        """
        Resumes the pipeline after human analyst review or Maker-Checker approval.
        """
        tier = state.hitl_tier

        # Enforce Maker-Checker for T2 and T3
        if tier in (RiskTier.T2, RiskTier.T3) and not checker_id:
            raise PermissionError(
                f"Tier {tier.value} requires dual Maker-Checker approval (checker_id missing)."
            )

        state.maker = maker_id
        state.checker = checker_id
        state.hitl_status = analyst_verdict

        # Feedback loop update
        if state.decision_record:
            self.feedback_loop.submit_feedback(
                case_id=state.dossier.get("case_id", f"CASE-{state.transaction.id}"),
                decision_id=state.decision_record.id,
                analyst_id=maker_id,
                verdict=analyst_verdict,
                notes=analyst_notes,
                rules_applied=state.risk_evaluation.get("evidence_ids", []),
            )

        # Commit final verdict to audit ledger
        audit_payload = {
            "decision": state.decision_record.model_dump(mode="json")
            if state.decision_record
            else {},
            "verdict": analyst_verdict,
            "maker": maker_id,
            "checker": checker_id,
            "notes": analyst_notes,
            "narrative": state.narrative.get("narrative_text", ""),
        }
        entry = self.audit_ledger.append(
            event_type=f"HITL_{analyst_verdict}_{tier.value}",
            entity_id=state.decision_record.id if state.decision_record else state.transaction.id,
            signer=f"maker:{maker_id}|checker:{checker_id or 'none'}",
            payload=audit_payload,
        )
        state.audit_hash = entry.verify_hash()
        return state
