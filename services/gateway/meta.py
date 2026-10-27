"""
Honest system-metadata probing for the ARGUS v2 gateway.

The /api/v2/meta endpoint must report ONLY what is actually true at request time:
 - llm_mode: whether the local Ollama runtime is reachable, otherwise the
   deterministic fallback extractor is in use (B14 wires the real LLM path; until
   then the honest answer is `deterministic_fallback` whenever Ollama is down).
 - chain_verified: the real result of AuditLedger.verify_chain().
 - last_event_seq: the real number of entries appended to the ledger.

No value in this module is faked. Every field is computed from live state.
"""

from __future__ import annotations

import socket
from urllib.parse import urlparse

from services.config import get_settings

# The pipeline's obligation extractor is deterministic by default (B14). The LLM
# path is used only when explicitly enabled AND Ollama is reachable; otherwise we
# honestly report the deterministic fallback. This flag is flipped on only when a
# real LLM extraction path is wired and healthy.
LLM_EXTRACTION_ENABLED = False


def ollama_reachable(timeout_s: float = 0.25) -> bool:
    """True iff the configured Ollama runtime accepts a TCP connection now."""
    settings = get_settings()
    parsed = urlparse(settings.OLLAMA_BASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 11434)
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except (OSError, ValueError):
        return False


def probe_llm_mode(timeout_s: float = 0.25) -> str:
    """Honest llm_mode for the UI badge (B14).

    Returns 'ollama' only when the LLM extraction path is actually enabled AND
    Ollama is reachable. Since the shipped pipeline uses the deterministic
    extractor, the honest answer is 'deterministic_fallback' even if an Ollama
    server happens to be listening — the UI must not claim an LLM it isn't using.
    """
    if LLM_EXTRACTION_ENABLED and ollama_reachable(timeout_s):
        return "ollama"
    return "deterministic_fallback"
