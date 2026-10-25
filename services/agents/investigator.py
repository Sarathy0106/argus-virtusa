"""
Investigator Agent for ARGUS Mesh.
Skill: case.gather_evidence
Pulls bitemporal customer profile, historical decisions, and counterparty subgraphs
to assemble comprehensive case dossiers.
"""

from datetime import UTC, datetime
from typing import Any

from contracts.agents import AgentCard, AgentSkill
from contracts.transactions import Transaction
from services.agents.crypto import AgentKeyPair
from services.memory.bitemporal import BitemporalMemoryStore


class InvestigatorAgent:
    def __init__(
        self,
        keypair: AgentKeyPair | None = None,
        memory_store: BitemporalMemoryStore | None = None,
    ):
        self.keypair = keypair or AgentKeyPair()
        self.memory = memory_store or BitemporalMemoryStore()

        self.card = AgentCard(
            agent_id="agent.investigator",
            name="Autonomous Financial Investigator Agent",
            version="1.0.0",
            public_key=self.keypair.public_key_hex,
            skills=[
                AgentSkill(
                    name="case.gather_evidence",
                    description="Assembles bitemporal facts, customer history, and counterparty graphs into an evidence dossier",
                )
            ],
        )

    def assemble_dossier(
        self,
        transaction: Transaction,
        risk_evaluation: dict[str, Any],
        query_time: datetime | None = None,
    ) -> dict[str, Any]:
        target_time = query_time or transaction.timestamp

        # Pull historical facts from bitemporal memory
        facts = self.memory.query_as_of(
            subject=transaction.account_token, as_of_valid_time=target_time
        )

        dossier = {
            "case_id": f"CASE-{transaction.id}",
            "primary_transaction_id": transaction.id,
            "account_token": transaction.account_token,
            "counterparty_token": transaction.counterparty_token,
            "amount": transaction.amount,
            "risk_score": risk_evaluation.get("risk_score", 0.0),
            "tier": risk_evaluation.get("tier", "T1"),
            "evidence_ids": risk_evaluation.get("evidence_ids", []),
            "bitemporal_facts": [
                {
                    "predicate": f.predicate,
                    "object": f.object,
                    "valid_from": f.valid_from.isoformat(),
                    "source": f.source,
                }
                for f in facts
            ],
            "top_risk_factors": risk_evaluation.get("top_factors", []),
            "investigation_timestamp": datetime.now(UTC).isoformat(),
        }
        return dossier
