"""
Intake Agent for ARGUS v2 (Stage 1).
Takes raw regulatory circular text, applies PII Airlock tokenization,
chunks the document into deterministic numbered clauses, assigns bitemporal
valid-time coordinates, and computes SHA-256 integrity hash.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from contracts.agents import AgentCard, AgentSkill
from contracts.memory import RegulationClause
from services.agents.crypto import AgentKeyPair
from services.airlock.airlock import PIIAirlock


class IntakeAgent:
    def __init__(self, airlock: PIIAirlock | None = None, key_pair: AgentKeyPair | None = None):
        self.key_pair = key_pair or AgentKeyPair()
        self.airlock = airlock or PIIAirlock()
        self.agent_id = "agent.intake"
        self.card = AgentCard(
            agent_id=self.agent_id,
            name="Regulatory Intake Agent",
            version="2.0.0",
            public_key=self.key_pair.public_key_hex,
            skills=[
                AgentSkill(
                    name="intake.parse_circular",
                    description="Tokenizes, chunks, and temporally indexes a regulatory circular.",
                )
            ],
        )

    def process_circular(
        self,
        circular_id: str,
        circular_title: str,
        raw_text: str,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Executes Stage 1 Circular Intake:
        1. Tokenizes any sensitive entity info via PII Airlock.
        2. Computes canonical SHA-256 document hash.
        3. Chunks into structured RegulationClause objects.
        """
        # Step 1: PII Airlock Tokenization
        tokenized_text = self.airlock.tokenize_text(raw_text, scope=f"CIRCULAR_{circular_id}")

        # Step 2: Content Hash
        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        # Step 3: Clause Chunking
        effective_from = valid_from or datetime.now(timezone.utc)
        effective_to = valid_to or datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        clauses = self._chunk_clauses(
            circular_id=circular_id,
            circular_title=circular_title,
            text=tokenized_text,
            valid_from=effective_from,
            valid_to=effective_to,
        )

        return {
            "circular_id": circular_id,
            "circular_title": circular_title,
            "document_hash": content_hash,
            "clause_count": len(clauses),
            "clauses": clauses,
            "airlocked": True,
        }

    def _chunk_clauses(
        self,
        circular_id: str,
        circular_title: str,
        text: str,
        valid_from: datetime,
        valid_to: datetime,
    ) -> list[RegulationClause]:
        """
        Splits circular text into discrete clauses based on clause/section markers.
        """
        # Look for patterns like "Clause 1.", "1.", "Section 2:", "Paragraph (a)", etc.
        pattern = r"(?:\n|^)(?:(?:Section|Clause|Paragraph|\§)\s*([0-9A-Za-z\.\-]+)|([0-9]+)\.)[:\s]"
        splits = list(re.finditer(pattern, text, re.IGNORECASE))

        clauses: list[RegulationClause] = []

        if not splits:
            # Fallback: Treat paragraphs as clauses
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for idx, p in enumerate(paragraphs, 1):
                cid = f"{circular_id}-C{idx:02d}"
                first_line = p.split("\n")[0][:80]
                clauses.append(
                    RegulationClause(
                        id=cid,
                        doc_id=circular_id,
                        clause_ref=cid,
                        title=f"{circular_title} - {first_line}",
                        clause_text=p,
                        valid_from=valid_from,
                        valid_to=valid_to,
                    )
                )
            return clauses

        for i, match in enumerate(splits):
            start = match.start()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            chunk = text[start:end].strip()

            marker = match.group(1) or match.group(2) or f"{i+1}"
            cid = f"{circular_id}-C{marker.replace('.', '')}"
            lines = chunk.split("\n")
            title = lines[0].strip()[:100]

            clauses.append(
                RegulationClause(
                    id=cid,
                    doc_id=circular_id,
                    clause_ref=cid,
                    title=f"{circular_id}: {title}",
                    clause_text=chunk,
                    valid_from=valid_from,
                    valid_to=valid_to,
                )
            )

        return clauses
