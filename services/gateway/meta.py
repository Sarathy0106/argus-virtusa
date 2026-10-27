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

# B14 LLM extraction is wired (Ollama + citation verifier + replay cache). It is
# enabled when ARGUS_LLM_EXTRACTION=1. The ACTUAL mode that ran a case is reported
# via report_extraction_mode(); /meta reflects the real mode, not just a flag.
import os
import socket
from urllib.parse import urlparse

from services.config import get_settings

LLM_EXTRACTION_ENABLED = os.environ.get("ARGUS_LLM_EXTRACTION", "0") == "1"

# Last obligation-extraction mode observed from a real pipeline run.
_LAST_EXTRACTION_MODE: str | None = None


def report_extraction_mode(mode: str) -> None:
    """Called by the pipeline runner after each case so /meta can report the mode
    that actually produced obligations (ollama / replay_cache / deterministic)."""
    global _LAST_EXTRACTION_MODE
    _LAST_EXTRACTION_MODE = mode


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

    Prefers the ACTUAL mode of the most recent extraction (ollama / replay_cache /
    deterministic). Before any case has run, reflects whether the LLM path is
    enabled and Ollama is reachable; otherwise the honest deterministic fallback.
    """
    if _LAST_EXTRACTION_MODE:
        return _LAST_EXTRACTION_MODE
    if LLM_EXTRACTION_ENABLED and ollama_reachable(timeout_s):
        return "ollama"
    return "deterministic_fallback"
