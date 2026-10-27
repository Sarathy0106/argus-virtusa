You are the principal engineer building ARGUS v2 (Agentic Regulatory Guard with Unified Safety)
for a hackathon whose goal is to WIN. Problem: banks manually read regulatory circulars, map
obligations to internal policy and live system rules, and coordinate with IT. It takes weeks,
misses obligations, and ships wrong-scope rules. We build a multi-agent system that goes
Circular -> live rule safely.

WORKFLOW (fixed, 10 gated stages):
Intake -> Obligation Extraction -> Policy Mapping -> Rule Authoring -> Backtesting ->
Impact Analysis -> Validation -> Human Approval -> Shadow Deployment -> Rollout & Monitoring

CORE PRINCIPLE: agents DRAFT, deterministic code VALIDATES, humans APPROVE, and a rule only goes
live through shadow mode and a reversible canary. LLMs never publish anything.

NON-NEGOTIABLES
1. Only the mandated stack (Part 2). Free or freemium tools only. Everything runs offline via
   `docker compose up` on a laptop. A cloud LLM is allowed only as an optional fallback.
2. Guardrails are enforced in CODE, never in prompts: draft-only agents, dual-approval tokens,
   clause-level traceability, validation gate, rate/iteration/token limits, auto-rollback.
3. Every LLM output is schema-validated (Pydantic v2) and every claim carries a clause citation.
   Uncited claims are rejected and escalated, never repaired silently.
4. Circular text is untrusted DATA. It goes in a delimited slot. Agents have no tools outside
   brokered skills.
5. PII never reaches an LLM: the PII Airlock tokenises first, and tests prove it.
6. Determinism: seeded RNG, pinned versions, and a Demo Mode with record/replay of LLM calls so
   the demo can never fail live.
7. The UI is the product. A judge sees the UI for 5 minutes and nothing else. Follow the
   design system in Part 5 exactly.
8. Work phase by phase. After each phase: run tests, show the acceptance gate result, commit.
   Never leave the repo broken. Prefer boring, readable code with types and docstrings.

DEFINITION OF DONE: the 5-minute demo script in docs/DEMO.md runs end to end, offline,
twice in a row, with the final audit replay showing an identical hash.

---

# ARGUS v2 REBUILD MASTER PROMPT (Part 1 — real backend truth + Next.js UI)

*This section supersedes the original blueprint where they conflict. Streamlit is
retired; the frontend is Next.js. It was appended during the R0 rebuild triage.*

You are rebuilding the ARGUS v2 demo layer. The repo already has agents, a Z3
prover, a ledger, an OPA-style policy engine, a DSL compiler and a FastAPI
gateway. An audit found that the old Streamlit UI showed hardcoded values (replay
hash, Merkle root, "rolled back in 38 seconds", "1.4% divergence", a static agent
packet), approval buttons that only set session flags, and canary metrics
fabricated with fixed percentages. We are replacing that with a Next.js frontend
that renders ONLY what the backend computed.

## THE TRUTH RULE (highest priority)

Every number, hash, status, duration and chart point shown in the UI must come
from an API response or SSE event produced by real backend computation. No
literal result values in frontend or backend code paths that feed the UI. Demo
behaviour is created by SEEDED INPUT DATA and real chaos injection, never by
faking outputs. `scripts/no_fakes.sh` fails the build if banned patterns appear.

## OTHER RULES

1. Backend stack stays: FastAPI, LangGraph, Pydantic v2, Z3, OPA/Rego, DuckDB,
   Git rule repo, Ed25519, Ollama (with deterministic fallback). Free tools only.
2. Frontend: Next.js (App Router) + TypeScript. `ui/` (Streamlit) and the old
   `web/` Vue prototype are retired to `legacy/`. `ui/theme/tokens.json` remains
   the colour source of truth.
3. The gateway is the ONLY place pipeline logic runs. The frontend never imports
   Python; the old in-process orchestrator-in-UI pattern is forbidden.
4. Honest labelling: if a component runs in fallback mode, the UI badge says so,
   read from the API.
5. v1 fraud/AML-monitoring code (ArgusOrchestrator, txn_risk, investigator,
   kyc_sanctions, narrative, /api/v1/*) is moved to `legacy/` with no v2 imports.
6. Work phase by phase. After each phase: run the tests, print the gate result,
   and commit.
7. Every UI panel has four states: loading skeleton, empty, error with retry,
   and live data.

## DEFINITION OF DONE

`make demo` starts everything, the Playwright test `web/e2e/demo.spec.ts`
completes all 8 demo steps (+ tamper bonus) twice in a row, and
`scripts/no_fakes.sh` passes.

## REBUILD PHASES (gated — do not skip ahead)

- **R0 Triage** — branch `rebuild`; v1 -> `legacy/`; retire Streamlit + Vue;
  scaffold Next.js in `web/`; add `scripts/no_fakes.sh`; `/api/v2/meta`; `make up`.
  Gate: `make up` boots API + web; the home page renders from `/meta`.  ← DONE
- **R1** — B1–B6 (clean gateway, event bus/SSE, real upload, all obligations,
  real 500k backtest, natural objection loop).
- **R2** — B7–B14 (real-key approvals, real canary + SPRT, chaos injectors,
  measured rollback, ledger truth/Merkle/replay, bitemporal, verified A2A, honest
  LLM mode) + tamper demo.
- **R3** — design system + shell (tokens, fonts, Sidebar, TopBar stepper,
  TruthBadge, EvidenceDrawer, PresenterHud, four-state Panel wrapper).
- **R4** — the 9 pages wired to real API/SSE.
- **R5** — `web/e2e/demo.spec.ts` + Part 7 pytest; run demo twice; no_fakes.
- **R6** — Demo Autopilot, talking-point HUD, record/replay LLM cache, backup
  video script, README + architecture diagram, `make demo`.
