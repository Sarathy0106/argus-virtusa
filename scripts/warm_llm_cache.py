#!/usr/bin/env python3
"""
Warm the LLM obligation-extraction cache for the 4 preset circulars (C1-C4).

Run this once before a live demo (with Ollama running) so every preset extracts
instantly from the cache and never waits on a cold model call:

    make warm-llm

After warming, the demo works even if Ollama is stopped — the cache replays.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.agents.intake_agent import IntakeAgent  # noqa: E402
from services.cognition.llm_extractor import extract_clause_obligations  # noqa: E402

CIRCULARS = Path(__file__).resolve().parent.parent / "data" / "circulars"
FILES = [
    "C1_cash_deposit_edd.md",
    "C2_coop_nbfc_lending.md",
    "C3_upi_merchant_limits.md",
    "C4_poisoned_circular.md",
]


def main() -> None:
    intake = IntakeAgent()
    for fname in FILES:
        path = CIRCULARS / fname
        if not path.exists():
            print(f"  [skip] {fname} not found")
            continue
        clauses = intake.process_circular(fname[:2], fname, path.read_text())["clauses"]
        print(f"{fname}: {len(clauses)} clauses")
        for cl in clauses:
            t0 = time.time()
            out = extract_clause_obligations(cl.clause_text)
            print(
                f"  {cl.id}: mode={out.mode} verified={out.verified_count} "
                f"rejected={out.rejected_count} ({time.time() - t0:.1f}s)"
            )
    print("\nLLM cache warmed. Presets will now extract instantly (replay_cache).")


if __name__ == "__main__":
    main()
