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


def probe_llm_mode(timeout_s: float = 0.25) -> str:
    """Return 'ollama' only if the configured Ollama runtime accepts a TCP
    connection right now, otherwise 'deterministic_fallback'. This is a real
    probe: if Ollama is not running, the UI badge will honestly say fallback.
    """
    settings = get_settings()
    parsed = urlparse(settings.OLLAMA_BASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 11434)
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return "ollama"
    except (OSError, ValueError):
        return "deterministic_fallback"
