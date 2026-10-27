"""
Tamper demo (B11 bonus).

Operates on a COPY of the live ledger so the real chain is never mutated. Flips a
bit in a chosen entry's payload, then runs verify_chain on the copy to surface the
first broken index — this is what makes the replay/integrity feature visibly
meaningful in the Audit page.
"""

from __future__ import annotations

from typing import Any

from services.ledger.ledger import GENESIS_HASH, AuditChainIntegrityError, AuditLedger


def run_tamper_demo(ledger: AuditLedger, target_seq: int) -> dict[str, Any]:
    """Return a before/after integrity report after tampering a COPY at
    target_seq. The live ledger is untouched."""
    original_entries = ledger.snapshot()
    if not (1 <= target_seq <= len(original_entries)):
        raise IndexError(f"target_seq {target_seq} out of range (1..{len(original_entries)})")

    # Build a fresh ledger from the snapshot (copy), then corrupt one entry.
    copy = AuditLedger(deterministic=ledger.deterministic)
    copy._chain = original_entries  # type: ignore[attr-defined]

    before_verified, before_root = _status(copy)

    # Flip a bit in the target entry's payload_hash (a stored field feeding the
    # entry hash) so the chain breaks at exactly this index.
    entry = copy._chain[target_seq - 1]  # type: ignore[attr-defined]
    tampered_payload_hash = _flip_first_hex(entry.payload_hash)
    entry.payload_hash = tampered_payload_hash

    after_verified, broken_index, after_root = _verify_named(copy)

    return {
        "target_seq": target_seq,
        "tampered_field": "payload_hash",
        "before": {"verified": before_verified, "merkle_root": before_root},
        "after": {
            "verified": after_verified,
            "first_broken_index": broken_index,
            "merkle_root": after_root,
        },
        "note": "Tampering was applied to a copy; the live ledger is unchanged.",
    }


def _flip_first_hex(h: str) -> str:
    if not h:
        return "f"
    first = h[0]
    flipped = "0" if first != "0" else "1"
    return flipped + h[1:]


def _status(ledger: AuditLedger) -> tuple[bool, str]:
    try:
        return ledger.verify_chain(), ledger.merkle_root()
    except AuditChainIntegrityError:
        return False, GENESIS_HASH


def _verify_named(ledger: AuditLedger) -> tuple[bool, int | None, str]:
    try:
        ok = ledger.verify_chain()
        return ok, None, ledger.merkle_root()
    except AuditChainIntegrityError as exc:
        broken = None
        for tok in str(exc).split():
            stripped = tok.strip(":.,;")
            if stripped.isdigit():
                broken = int(stripped)
                break
        return False, broken, ledger.merkle_root()
