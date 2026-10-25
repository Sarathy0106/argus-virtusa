"""
Strict Egress Gate for ARGUS.
Inspects all outbound text, prompt contexts, and LLM responses.
Blocks and raises an immediate security exception if ANY raw identifier
or high-entropy secret escapes the vault perimeter.
"""

import math
import re

from services.airlock.recognizers import IndianPIIRecognizer


class PIILeakageError(Exception):
    """Raised when an egress payload contains un-tokenized sensitive identifiers."""

    def __init__(self, message: str, detected_kind: str, snippet: str):
        super().__init__(message)
        self.detected_kind = detected_kind
        self.snippet = snippet


# Backward-compatibility alias
PIILeakageException = PIILeakageError


def shannon_entropy(data: str) -> float:
    """Calculates Shannon entropy to detect raw cryptographic keys or secrets."""
    if not data:
        return 0.0
    entropy = 0.0
    for x in set(data):
        p_x = float(data.count(x)) / len(data)
        entropy += -p_x * math.log2(p_x)
    return entropy


class EgressGate:
    def __init__(self):
        self.recognizer = IndianPIIRecognizer()
        # High-entropy token pattern for hex/base64 secrets > 32 chars
        self.secret_pattern = re.compile(r"\b[0-9a-fA-F]{32,64}\b")

    def inspect_and_enforce(self, text: str, context_label: str = "outbound_payload") -> None:
        """
        Inspects text for any raw identifiers.
        Raises PIILeakageException if any raw PII is discovered.
        """
        # 1. Run Indian identifier scan
        entities = self.recognizer.analyze(text)
        for entity in entities:
            # Format-preserving tokens like <PAN_4B2C> are safe and allowed
            if entity.text.startswith("<") and entity.text.endswith(">"):
                continue

            # Masked sample for safe logging
            masked = entity.text[:2] + "****" + entity.text[-2:] if len(entity.text) > 4 else "****"
            raise PIILeakageException(
                f"[EGRESS_GATE_BLOCKED] Raw {entity.entity_type} detected in {context_label}: '{masked}'",
                detected_kind=entity.entity_type,
                snippet=masked,
            )

        # 2. Check for leaked high-entropy secrets (e.g. leaked AES keys)
        for match in self.secret_pattern.finditer(text):
            secret_str = match.group()
            if shannon_entropy(secret_str) > 3.8:  # High randomness threshold
                masked = secret_str[:4] + "...." + secret_str[-4:]
                raise PIILeakageException(
                    f"[EGRESS_GATE_BLOCKED] High-entropy secret detected in {context_label}: '{masked}'",
                    detected_kind="SECRET_KEY",
                    snippet=masked,
                )

    def is_safe(self, text: str) -> bool:
        """Returns True if the text contains zero raw identifiers, False otherwise."""
        try:
            self.inspect_and_enforce(text)
            return True
        except PIILeakageException:
            return False
