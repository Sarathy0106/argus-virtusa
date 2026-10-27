"""
Narrative (SAR / STR) Drafting Agent for ARGUS Mesh.
Skill: narrative.draft_sar
Produces evidence-bound narratives and Suspicious Activity Reports (SAR/STR).
Enforces citation verification and egress gate privacy checks.
"""

from typing import Any

from contracts.agents import AgentCard, AgentSkill
from services.agents.crypto import AgentKeyPair
from services.airlock.egress import EgressGate
from services.cognition.verifier.verifier import EvidenceVerifier


class NarrativeAgent:
    def __init__(
        self,
        keypair: AgentKeyPair | None = None,
        verifier: EvidenceVerifier | None = None,
        egress_gate: EgressGate | None = None,
    ):
        self.keypair = keypair or AgentKeyPair()
        self.verifier = verifier or EvidenceVerifier()
        self.egress_gate = egress_gate or EgressGate()

        self.card = AgentCard(
            agent_id="agent.narrative",
            name="Regulatory Narrative and SAR Drafting Agent",
            version="1.0.0",
            public_key=self.keypair.public_key_hex,
            skills=[
                AgentSkill(
                    name="narrative.draft_sar",
                    description="Drafts formal evidence-bound SAR/STR narrative with clause and evidence citations",
                )
            ],
        )

    def draft_narrative(self, dossier: dict[str, Any]) -> dict[str, Any]:
        """
        Drafts deterministic baseline template and verified narrative citing evidence IDs.
        Gated by EvidenceVerifier and EgressGate.
        """
        evidence_ids = dossier.get("evidence_ids", [])
        acct = dossier.get("account_token", "<UNKNOWN_ACCT>")
        dest = dossier.get("counterparty_token", "<UNKNOWN_DEST>")
        amount = dossier.get("amount", 0.0)
        risk_score = dossier.get("risk_score", 0.0)
        tier = dossier.get("tier", "T1")

        # 1. Deterministic Fallback Template
        template_text = (
            f"SUSPICIOUS ACTIVITY DOSSIER (Tier: {tier}, Score: {risk_score:.4f})\n"
            f"Account {acct} executed transaction of INR {amount:,.2f} to {dest}.\n"
            f"Triggered Rule Nodes: {', '.join(evidence_ids)}."
        )

        # 2. Polished Evidence-Bound Text with explicit citations
        cited_statements = []
        for evid in evidence_ids:
            cited_statements.append(f"Activity matches detection pattern for {evid} [EVID:{evid}].")

        polished_candidate = (
            f"SAR INVESTIGATION REPORT - Case {dossier.get('case_id', 'N/A')}\n\n"
            f"Summary: Account {acct} initiated an anomalous transfer of INR {amount:,.2f} "
            f"destined for counterparty {dest} at calibrated risk probability {risk_score:.2%}.\n\n"
            f"Evidence & Justification:\n" + "\n".join(f"- {s}" for s in cited_statements)
        )

        # 3. Evidence Verifier Gate
        verification = self.verifier.verify_and_gate(
            candidate_text=polished_candidate,
            valid_evidence_ids=evidence_ids,
            fallback_template=template_text,
        )

        # 4. Strict Egress Gate Check
        self.egress_gate.inspect_and_enforce(
            verification.approved_text, context_label="sar_narrative"
        )

        return {
            "case_id": dossier.get("case_id"),
            "narrative_text": verification.approved_text,
            "is_verified": verification.is_valid,
            "cited_ids": verification.cited_ids,
            "hallucinated_ids": verification.hallucinated_ids,
            "tier": tier,
        }
