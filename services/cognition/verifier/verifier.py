"""
Evidence and Citation Verifier for ARGUS.
Enforces that all narrative claims cite legitimate evidence IDs or regulation clause IDs.
Hallucinated or uncited claims trigger immediate fallback to deterministic templates.
"""

import re

from pydantic import BaseModel


class VerificationResult(BaseModel):
    is_valid: bool
    cited_ids: list[str]
    hallucinated_ids: list[str]
    approved_text: str
    rejection_reason: str | None = None


# Citation regex e.g. [EVID:aml_structuring_window] or [CLAUSE:RBI-KYC-C23]
CITATION_PATTERN = re.compile(r"\[(EVID|CLAUSE):([a-zA-Z0-9_\-]+)\]")


class EvidenceVerifier:
    def verify_and_gate(
        self, candidate_text: str, valid_evidence_ids: list[str], fallback_template: str
    ) -> VerificationResult:
        """
        Extracts citations from candidate_text and validates them against valid_evidence_ids.
        If any citation refers to non-existent evidence or no valid citations exist,
        rejects candidate_text and falls back to deterministic template.
        """
        valid_set = set(valid_evidence_ids)
        matches = CITATION_PATTERN.findall(candidate_text)

        if not matches:
            return VerificationResult(
                is_valid=False,
                cited_ids=[],
                hallucinated_ids=[],
                approved_text=fallback_template,
                rejection_reason="No verifiable citations found in narrative. Enforced template fallback.",
            )

        cited_ids = [m[1] for m in matches]
        hallucinated = [cid for cid in cited_ids if cid not in valid_set]

        if hallucinated:
            return VerificationResult(
                is_valid=False,
                cited_ids=cited_ids,
                hallucinated_ids=hallucinated,
                approved_text=fallback_template,
                rejection_reason=f"Hallucinated citations detected: {hallucinated}. Enforced template fallback.",
            )

        return VerificationResult(
            is_valid=True,
            cited_ids=cited_ids,
            hallucinated_ids=[],
            approved_text=candidate_text,
            rejection_reason=None,
        )
