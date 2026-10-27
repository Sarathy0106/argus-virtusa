# ARGUS v2 — Regulatory Circular → Live Rule Engine

> *"Circular in, safe rule out."* Every number in the UI is computed live by the
> backend; click any metric to see the event behind it.

ARGUS v2 turns a regulatory circular into a safe, deployed rule through 10 gated
stages: **agents draft, deterministic code validates, humans approve, and a rule
goes live only through shadow mode and a reversible, SPRT-monitored canary.**

This is the rebuilt demo layer (see `CLAUDE.md`): a **FastAPI** backend of record
and a **Next.js** Mission Control frontend. The retired Streamlit/Vue prototypes
live in `legacy/`.

---

## The Truth Rule

Every value shown in the UI comes from an API response or an SSE event produced by
**real computation** — real PDF extraction, a real 500k-row DuckDB backtest, real
Z3 proofs, real Ed25519 signatures, a real Wald SPRT, and a real Merkle-rooted
hash chain. Demo behaviour comes from **seeded input data and real chaos
injection**, never from faked outputs. `scripts/no_fakes.sh` fails the build if
banned patterns (pre-baked hashes, fixed result multipliers, mock/fake markers)
appear in the UI or the code paths that feed it.

---

## Architecture

```text
┌──────────────────────────── Next.js Mission Control (web/) ────────────────────────────┐
│  Inbox · Obligations · Rule Studio · Agent Mesh · Impact · Approvals · Rollout · Audit  │
│  TruthBadge · EvidenceDrawer (click any metric → source event, seq, entry_hash, JSON)   │
└───────────────┬──────────────────────────────── SSE + REST (same origin, proxied) ─────┘
                │
┌───────────────▼──────────────────────────── FastAPI gateway (services/gateway) ────────┐
│  /api/v2: cases (async runner + SSE) · approvals (JWT + Ed25519) · deploy · chaos ·     │
│           audit (ledger/merkle/tamper) · memory (bitemporal as-of) · meta · /.well-known│
└───────────────┬─────────────────────────────────────────────────────────────────────── ┘
                │ emits ArgusEvents (monotonic seq, Last-Event-ID resume)
┌───────────────▼─ Event bus (services/events) ───────────────────────────────────────────┐
│  Orchestrator (10-stage state machine) ── one rule bundle per applicable obligation      │
│    Intake(PDF/MD airlock+chunk) → Obligation+Applicability → Policy Map (Z3) →            │
│    Rule Author (naive first draft) → Backtest (DuckDB 500k) → Impact →                    │
│    Validator (Z3 ACTIVE_CONFLICT_UNRESOLVED + counter-example) → Approval → Shadow →      │
│    Rollout (live stream + Wald SPRT + chaos → measured rollback)                          │
│  Signed A2A mesh (Ed25519, broker-verified) · Append-only Merkle hash-chain ledger        │
└──────────────────────────────────────────────────────────────────────────────────────── ┘
Data: data/parquet/transactions_500k.parquet (500k rows) · data/circulars/C1–C4 · Git rules
```

---

## Quickstart

```bash
# Backend deps already in .venv (uv). Frontend:
make install-web

# Dev: API on :8000, web on :3000 (web proxies /api/* to the gateway)
make up

# Or separately
make api      # FastAPI gateway
make web      # Next.js dev server
```

Open http://localhost:3000, click **Run C1** (or **Demo Autopilot**), and watch the
pipeline stream live.

### Tests & gates

```bash
make test       # pytest: 75 tests incl. one per demo step
make no-fakes   # anti-fake CI gate
cd web && pnpm build   # type-check + lint the frontend
make demo       # boot stack + run the Playwright 8-step demo (twice)
```

### Real LLM obligation extraction (Ollama, optional)

By default the obligation extractor is deterministic (keyword + regex), so the
demo runs fully offline. To use the real LLM path (B14):

```bash
ollama pull qwen2.5:7b     # one-time
make warm-llm              # pre-extract the 4 presets into the replay cache
make api-llm               # gateway with ARGUS_LLM_EXTRACTION=1
make web                   # (separate terminal)
```

The LLM path is wording-independent (handles rephrased circulars), but stays
safe: a **deterministic citation verifier** drops any obligation not grounded in
the clause text, a **prompt-injection guard** neutralises poisoned clauses (C4)
before the model sees them, vague non-executable advisories are rejected, and a
**record/replay cache** makes repeat runs instant and offline-safe. `/meta`
honestly reports the mode that actually ran: `ollama`, `replay_cache`, or
`deterministic_fallback`.

---

## The 8-step demo (≈5 min)

| # | Action | Proof on screen |
|---|---|---|
| 1 | Drag C1 PDF into Inbox | Clauses stream; Airlock tokenises entities |
| 2 | Open Obligations | Applicable vs Not (C2 n/a; C4 injection ignored) |
| 3 | Rule Studio | Z3 counter-example banner (the exact transaction) |
| 4 | Agent Mesh | Validator rejects; objection loop; iteration 2 passes |
| 5 | Impact | 500,000 rows processed; real before/after delta |
| 6 | Approvals | One signature → real 403; then maker + checker sign |
| 7 | Rollout + Chaos | Canary ladder, SPRT; `alert_flood` → measured rollback |
| 8 | Audit | Replay/merkle verify; **tamper** turns the chain red at the first broken index |

**Closing line:** *"Every number you saw was computed live, and you could click any of them to see the event behind it."*

---

## Key guarantees (verified)

- Real 500k DuckDB backtest; delta equals an independent count; threshold-sensitive.
- Natural objection loop: naive first draft → Z3 `ACTIVE_CONFLICT_UNRESOLVED` with a
  counter-example → iteration 2 passes (bounded ≤ 3).
- Per-user Ed25519 approvals: one-sig / maker==checker / post-sign tamper all → 403.
- Wald SPRT: healthy stream reaches 100%; a chaos flood crosses H1 and rolls back —
  no force-breach flag, no fixed multipliers.
- Measured rollback time (monotonic clock); Merkle root + inclusion proofs; tamper
  demo runs on a copy and names the first broken index.
- Honest `llm_mode` on `/meta` — the UI never claims an LLM it isn't using.
