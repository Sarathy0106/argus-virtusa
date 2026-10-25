"""
Unified PII Airlock for ARGUS.
Coordinates entity recognition, format-preserving vault tokenization,
and egress verification.
"""

from services.airlock.egress import EgressGate
from services.airlock.recognizers import IndianPIIRecognizer
from services.airlock.vault import PIIVault


class PIIAirlock:
    def __init__(self, vault: PIIVault | None = None):
        self.vault = vault or PIIVault()
        self.recognizer = IndianPIIRecognizer()
        self.egress = EgressGate()

    def tokenize_text(self, text: str, scope: str = "default_session") -> str:
        """
        Extracts all raw PII from text, stores encrypted values in the vault,
        and returns text with format-preserving tokens (<PAN_XXXX>, <AADHAAR_XXXX>, etc.).
        """
        entities = self.recognizer.analyze(text)
        if not entities:
            return text

        # Sort entities by start position descending so replacements don't shift earlier offsets
        entities.sort(key=lambda e: e.start, reverse=True)

        tokenized = text
        for entity in entities:
            # Skip if already a token
            if entity.text.startswith("<") and entity.text.endswith(">"):
                continue

            token = self.vault.tokenize_and_store(
                kind=entity.entity_type, raw_value=entity.text, scope=scope
            )
            tokenized = tokenized[: entity.start] + token + tokenized[entity.end :]

        return tokenized

    def detokenize_text(
        self, text: str, requesting_role: str, scope: str = "default_session"
    ) -> str:
        """
        Replaces vault tokens in text with their decrypted plaintext.
        Only allowed for authorized roles.
        """
        # Look for tokens in format <KIND_XXXXXX>
        import re

        token_regex = re.compile(r"<([A-Z]+)_[0-9A-F]{6}>")

        def replacer(match: re.Match) -> str:
            token = match.group(0)
            if self.vault.has_token(token):
                try:
                    return self.vault.detokenize(
                        token, requesting_role=requesting_role, scope=scope
                    )
                except PermissionError:
                    return token
            return token

        return token_regex.sub(replacer, text)

    def verify_egress(self, outbound_text: str, context_label: str = "llm_payload") -> None:
        """Ensures that outbound text contains zero raw identifiers."""
        self.egress.inspect_and_enforce(outbound_text, context_label=context_label)
