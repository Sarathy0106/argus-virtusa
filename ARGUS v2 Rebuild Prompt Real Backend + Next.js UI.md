# ARGUS v2 Rebuild Prompt: Real Backend Truth + Next.js Mission Control

*Companion to the first master prompt. It is based on a code audit of your zip: the backend skeleton is decent, the Streamlit UI is mostly a mock-up. This pack fixes both. Where it conflicts with the first prompt, this one wins (Streamlit is retired).*

## How to use

1. Append **Part 1** to `CLAUDE.md` in the repo root.
2. Run the **Part 8 phases** in order. Each phase has a gate, so do not skip ahead.
3. **Part 7 tests** are what make the demo trustworthy. A phase is not done until its tests pass.

---

# PART 1: REBUILD MASTER PROMPT (paste into the IDE)

```text
You are rebuilding the ARGUS v2 demo layer. The repo already has agents, a Z3 prover, a ledger,
an OPA-style policy engine, a DSL compiler and a FastAPI gateway. An audit found that the
Streamlit UI shows hardcoded values (replay hash, Merkle root, 'rolled back in 38 seconds',
'1.4% divergence', a static agent packet), approval buttons that only set session flags, and
canary metrics fabricated with fixed percentages. We are replacing that with a Next.js
frontend that renders ONLY what the backend computed.

THE TRUTH RULE (highest priority)
Every number, hash, status, duration and chart point shown in the UI must come from an API
response or SSE event produced by real backend computation. No literal result values in
frontend or backend code paths that feed the UI. Demo behaviour is created by SEEDED INPUT DATA
and real chaos injection, never by faking outputs. A CI script (scripts/no_fakes.sh) fails the
build if banned patterns appear (see Part 7).

OTHER RULES
1. Backend stack stays as in the blueprint: FastAPI, LangGraph, Pydantic v2, Z3, OPA/Rego,
   DuckDB, Git rule repo, Ed25519, Ollama (with deterministic fallback). Free tools only.
2. Frontend: Next.js (App Router) + TypeScript. Retire ui/ (Streamlit) and the old web/ Vue
   prototype. Keep ui/theme/tokens.json as the colour source of truth.
3. The gateway is the ONLY place pipeline logic runs. The frontend never imports Python and
   the old in-process orchestrator-in-UI pattern is forbidden.
4. Honest labelling: if a component runs in fallback mode (e.g. deterministic extraction
   instead of the LLM), the UI badge must say so, read from the API.
5. Remove v1 fraud/AML-monitoring code from the gateway (/api/v1/*, ArgusOrchestrator,
   txn_risk, investigator, kyc_sanctions) or move it to legacy/ with no imports from v2.
6. Work phase by phase. After each phase run the tests, print the gate result, and commit.
7. Every UI panel has four states: loading skeleton, empty, error with retry, and live data.

DEFINITION OF DONE
`make demo` starts everything, the Playwright test e2e/demo.spec.ts completes all 8 demo steps
(+ tamper bonus) twice in a row, and scripts/no_fakes.sh passes.
```

---

# PART 2: BACKEND WORK ORDERS

Each order names the file to change and the acceptance test. File paths are from your zip.

| # | Work order | Files | Acceptance test |
| --- | --- | --- | --- |
| B1 | **Clean gateway.** Delete v1 routes. Create versioned routers under `/api/v2`: `cases`, `approvals`, `deploy`, `chaos`, `audit`, `memory`, `meta`. Remove `allow_origins=['*']` and use the web origin only | `services/gateway/` | OpenAPI lists no `/api/v1`; `pytest tests/api` passes |
| B2 | **Event bus + async runner.** Add `services/events/bus.py` (asyncio pub/sub, append-only `events` table, `seq` numbers). The orchestrator emits an event at every stage start/end, agent message, objection, canary step. Run pipelines as background tasks; `POST /cases` returns `case_id` immediately. SSE at `GET /api/v2/cases/{id}/events` with `Last-Event-ID` resume | `services/orchestrator/v2_state_machine.py`, new `services/events/` | Test subscribes to SSE and sees stages 1..8 in order with increasing `seq` |
| B3 | **Real upload.** `POST /cases` accepts multipart (PDF, MD, TXT) or `preset_id`. Extract PDF text with pdfplumber, run the Airlock, then the clause chunker | `intake_agent.py`, gateway | Upload C1 as a PDF; clause count and clause IDs match the markdown version |
| B4 | **Process every applicable obligation.** Replace `target_obligation = applicable[0]` and `mappings[0]` with a loop that produces one rule bundle per obligation. The UI shows a list and lets the user pick | `v2_state_machine.py` | C1 yields at least 2 bundles; each has a full clause-to-rule trace |
| B5 | **Real backtest on 500k.** Load `data/parquet/transactions_500k.parquet` with DuckDB and evaluate the draft and current rule over it. Emit `backtest.progress` events. Return baseline vs draft alert counts, per-segment deltas, ops-load estimate | `backtest_agent.py`, `impact_agent.py` | Backtest runs under 30 s on a laptop; the delta is computed from rows, never constants |
| B6 | **Natural objection.** The Rule Author's first draft must be naive: it does not consult the conflict list. Remove the special case `if iteration == 1 and mapping.status == DETECTED`. The Z3-backed Validator then rejects it for a genuine reason and the Orchestrator re-routes | `rule_author_agent.py`, `validator_agent.py` | C1 first draft fails with `ACTIVE_CONFLICT_UNRESOLVED`, a Z3 counter-example is returned, and iteration 2 passes. C3 passes on iteration 1 (no loop) |
| B7 | **Human approval with real keys.** Create per-user Ed25519 keys for 4 demo users (`maker`, `checker`, `compliance`, `admin`) via `scripts/keygen.py`; a simple JWT login is enough (Keycloak is optional). `POST /approvals/maker` and `/approvals/checker` sign the bundle hash with the logged-in user's key. Remove the agent-key-as-human shortcut in `grant_dual_approval`. The Deployment Agent verifies both signatures and rejects maker == checker | `approvals` router, `deployment_agent.py`, `crypto.py` | Deploy with one signature returns 403; same user twice returns 403; tampering with the bundle after signing returns 403 |
| B8 | **Real canary and SPRT.** Add `services/traffic/stream.py` that generates a live stream at N tps (seeded, mild drift). Shadow and each canary step evaluate the candidate rule on that stream; metrics are measured: alert rate, decline rate, p95 latency via `time.perf_counter` around the actual evaluation. Implement **Wald SPRT** (`services/rollout/sprt.py`) comparing the observed alert rate with the backtest-predicted rate. Delete the `* 0.04` and `* 0.01` constants and the `force_canary_breach` flag | `deployment_agent.py`, `monitor_agent.py`, new `rollout/` | Healthy stream: ladder reaches 100%. Under a chaos flood: SPRT accepts H1 and breach is detected without any flag |
| B9 | **Chaos injectors.** `POST /chaos/{kind}` with kinds `alert_flood`, `latency_spike`, `drift`. They modify the *stream* (e.g. push 3x of transactions over the threshold, add artificial delay), not the results | `services/traffic/chaos.py` | After `alert_flood`, `breach.detected` is emitted by the Monitor within 5 s |
| B10 | **Measured rollback.** The saga records `breach_detected_at` and `rollback_confirmed_at` (monotonic clock) and the active bundle pointer swap. The duration returned is the real difference. Rollback restores the previous signed Git tag | `deployment_agent.py` | `rollback_ms` is within 10% of measured wall time; the previous bundle hash equals the pre-deploy hash |
| B11 | **Ledger truth.** In `ledger.py` add `merkle_root()`, `inclusion_proof(i)` and `verify_chain()`. In `replay.py` the replay re-executes from stored `input_hash`, `rule_version`, `model_version` and `seed` and returns the original and recomputed hash. Hash content only, excluding wall-clock fields. Remove the hardcoded 2026-10-26 timestamp from the deterministic mode (use an injected clock) | `services/ledger/` | Replay of 20 random decisions matches 100%. Flip one byte in a stored entry: `verify_chain` fails and names the first broken index |
| B12 | **Bitemporal as-of.** Port valid-time/record-time to v2 tables for obligations and rules. `GET /memory/asof?date=&known_at=` returns which rule version was live and what we knew then | new `services/memory/` | Query for the day before C3's effective date returns the previous rule version |
| B13 | **A2A signatures are verified.** Even if transport stays in-process, every message is an A2A envelope signed by the sender and verified by the broker on receipt. Serve `/.well-known/agent.json` for each agent. A forged or modified envelope is rejected and logged | `broker.py` | Red-team test: tamper with an envelope, expect rejection and a ledger entry |
| B14 | **LLM mode, honestly.** Obligation extraction uses Ollama (Qwen2.5-7B) with Instructor/JSON-schema, followed by the deterministic citation verifier. If Ollama is unreachable, fall back to the deterministic extractor and expose `llm_mode` on `/meta`. Record/replay cache for demo | `obligation_agent.py`, `cognition/` | `/meta` shows `ollama` or `deterministic_fallback`; the UI badge matches it |

**Add the tamper bonus.** `POST /audit/tamper-demo` (admin only, demo flag) flips a bit in a chosen ledger entry on a *copy* of the chain so the UI can show the red break and the first broken index. It makes the replay feature visibly meaningful.

---

# PART 3: EVENT CONTRACT (SSE)

The contract is the heart of the live UI. Generate TypeScript types from the FastAPI OpenAPI (`openapi-typescript`) so the two sides cannot drift.

```ts
type ArgusEvent = {
  seq: number;            // monotonic per case, used for Last-Event-ID resume
  ts: string;             // ISO time from the server clock
  case_id: string;
  trace_id: string;
  type:
    | 'stage.started' | 'stage.completed'
    | 'agent.message'        // A2A envelope: from, to, skill, signature_ok
    | 'obligation.extracted' | 'applicability.decided'
    | 'conflict.proved'      // includes Z3 counter-example
    | 'objection.raised' | 'objection.resolved'
    | 'backtest.progress'    // processed, total, running_alert_delta
    | 'approval.signed'
    | 'shadow.sample' | 'canary.step' | 'sprt.update'
    | 'breach.detected' | 'rollback.completed'
    | 'ledger.appended' | 'chaos.injected';
  stage?: number;           // 1..10
  agent?: string;
  payload: Record<string, unknown>;
  entry_hash?: string;      // ledger hash of this event, shown in the evidence drawer
};
```

**Evidence drawer.** Every metric card and chip in the UI is clickable and opens a side drawer showing the source event(s), their `seq`, `entry_hash` and the raw JSON. This is your answer to "is this real?" in front of judges.

**Truth badge.** The footer of every page shows `Live from API · last event seq 482 · llm_mode ollama · chain verified ✓`, all read from `/meta` and the ledger.

---

# PART 4: FRONTEND STACK AND FOLDER STRUCTURE

| Need | Choice (all free, MIT/Apache) |
| --- | --- |
| Framework | **Next.js 15 (App Router) + TypeScript**, `pnpm` |
| Styling | **Tailwind CSS** + **shadcn/ui** (Radix primitives) |
| Animation | **Framer Motion** (`motion`) |
| Agent mesh, traceability graph | **@xyflow/react** (React Flow) with custom nodes and edges |
| Charts | **Apache ECharts** (`echarts-for-react`) for waterfall, heatmap, gauges; Recharts for simple lines |
| Rule DSL, Rego and diff | **Monaco Editor** (`@monaco-editor/react`, `DiffEditor`) |
| Server state | **TanStack Query**; SSE via `EventSource` wrapper in `lib/sse.ts` |
| Client state | **Zustand** (presenter mode, selected case, evidence drawer) |
| Validation | **zod** on every API response so bad data fails loudly |
| Types | `openapi-typescript` generated from FastAPI |
| Fonts | `next/font`: Space Grotesk, Inter, JetBrains Mono (self-hosted at build, so offline-safe) |
| E2E | **Playwright** |
| Icons | `lucide-react` |

```text
web/
├─ package.json  next.config.ts  tailwind.config.ts  playwright.config.ts
├─ app/
│  ├─ layout.tsx                  # fonts, providers, shell
│  ├─ (shell)/
│  │  ├─ page.tsx                 # Mission Control (home)
│  │  ├─ inbox/page.tsx           # Circular Inbox
│  │  ├─ obligations/page.tsx
│  │  ├─ studio/page.tsx          # Rule Studio
│  │  ├─ mesh/page.tsx            # live Agent Mesh
│  │  ├─ impact/page.tsx
│  │  ├─ approvals/page.tsx
│  │  ├─ rollout/page.tsx
│  │  └─ audit/page.tsx
├─ components/
│  ├─ ui/                         # shadcn primitives
│  ├─ shell/ (Sidebar, TopBar, TruthBadge, EvidenceDrawer, PresenterHud)
│  ├─ pipeline/ (StageStepper, StageCard)
│  ├─ mesh/ (AgentNode, PacketEdge, ObjectionLoop)
│  ├─ graph/ (TraceGraph)
│  ├─ studio/ (ClausePane, DslEditor, RuleDiff, CounterExampleBanner)
│  ├─ impact/ (BeforeAfterBars, SegmentHeatmap, OpsLoadCard)
│  ├─ rollout/ (CanaryLadder, SprtChart, ShadowOverlay, ChaosPanel)
│  └─ audit/ (HashChain, MerkleRoot, ReplayCard, AsOfQuery, TamperDemo)
├─ lib/ (api.ts, sse.ts, schemas.ts, format.ts, types.generated.ts)
├─ store/ (case.ts, presenter.ts, drawer.ts)
├─ styles/ (globals.css, tokens.css)
└─ e2e/ (demo.spec.ts, helpers.ts)
```

Backend additions: `services/events/`, `services/traffic/`, `services/rollout/`, `services/memory/`, `scripts/no_fakes.sh`, `legacy/` (v1 code).

---

# PART 5: DESIGN SYSTEM (carried over, now with exact CSS)

**Concept:** *Regulatory Mission Control*. Dark, calm, high-trust. Think Linear meets Datadog.

```css
:root {
  --bg:#0B0F17; --surface:#121826; --elevated:#1A2233; --border:#263047;
  --text:#E6EAF2; --muted:#8A94A8;
  --primary:#22D3EE; --accent:#6366F1;
  --ok:#22C55E; --warn:#F59E0B; --danger:#EF4444; --shadow:#A78BFA;
  --radius-card:12px; --radius-btn:10px; --radius-chip:999px;
}
```

- **Fonts:** headings Space Grotesk 600/700; body Inter 400/500/600; IDs, hashes, DSL JetBrains Mono. Scale in px: 12, 14, 16, 20, 24, 32, 48. Tabular numerals on every metric (`font-variant-numeric: tabular-nums`).
- **Layout:** 4px grid; spacing 4, 8, 12, 16, 20, 24, 32, 48. Content max width 1440px; sidebar 264px (72px collapsed); top bar 64px with the 10-stage stepper pinned. Cards: padding 20px, 1px border. Buttons: height 40px. Chips: height 24px.
- **Colour meaning is fixed:** cyan = agent activity, indigo = actions, green = pass, amber = objection/warning, red = fail/rollback, violet = shadow mode.
- **Motion:** 150-250ms ease-out. Animate only things that mean something: message packets travelling along mesh edges, count-ups when a real number arrives, the red rollback flash, the green hash-match pulse. Respect `prefers-reduced-motion`.
- **Glow** (`box-shadow: 0 0 24px #22D3EE33`) only on the agent that is currently running.
- **Accessibility:** contrast at least 4.5:1, icon plus label (never colour alone), full keyboard navigation, visible focus rings.
- **Responsive:** works at 1440, 1920 and 390 wide (mobile shows a stacked layout; the demo targets desktop).

---

# PART 6: PAGE SPECS (each maps to a demo step)

| Page | Data source | What must be on screen |
| --- | --- | --- |
| **Mission Control** (home) | `/cases`, `/meta`, SSE | Case list, stage stepper, KPI strip (time elapsed, obligations found, bundles drafted), Demo Autopilot button, Presenter Mode toggle |
| **Inbox** (step 1) | `POST /cases`, SSE | Drag-and-drop uploader (PDF/MD/TXT) plus 4 presets; clauses stream in one by one; PII tokens as `‹PERSON_1›` chips; Airlock counter (entities tokenised) |
| **Obligations** (step 2) | `/cases/{id}/obligations` | Obligation cards: actor, condition, action, deadline, clause chip, applicability verdict (Applicable / Not applicable / Needs review) with the reason. C2 must show Not applicable. C4 shows the poisoned clause flagged and ignored |
| **Rule Studio** (steps 3-4) | `/cases/{id}/mapping`, `/rules/{bundle}` | Left: clause. Right: Monaco DSL and compiled Rego. Bottom: generated tests. Z3 counter-example banner on conflict. Gap card with the missing-policy suggestion. Diff between iteration 1 and 2 |
| **Agent Mesh** (step 4) | SSE only | React Flow graph of 9 agents. Packets travel along edges on each `agent.message`; the Validator to Policy Mapper edge turns amber on `objection.raised`; iteration counter `1/3`; signature check icon per message; token/budget meter |
| **Impact** (step 5) | `/cases/{id}/impact` | Backtest progress bar (rows processed of 500,000), before/after bars, segment heatmap, false-positive and ops-load cards, objection if impact exceeds tolerance |
| **Approvals** (step 6) | `/approvals` | Login switcher for the demo users. Maker and checker panels with real signature status and public key fingerprints. Deploy button is disabled until both signatures verify. A visible "try with one signature" button that shows the real 403 |
| **Rollout** (step 7) | SSE | Shadow vs backtest overlay with divergence; canary ladder 1 -> 10 -> 50 -> 100; SPRT log-likelihood chart with accept/reject bounds; latency and decline gauges; Chaos panel (`alert_flood`, `latency_spike`, `drift`); on breach a red flash and a banner with the measured `rollback_ms` |
| **Audit** (step 8) | `/audit/*` | Hash-chain strip, real Merkle root, Replay button showing original vs recomputed hash and verdict, as-of query (date and known-at pickers), Tamper demo (red break at the first broken index) |

**Presenter HUD:** a toggle that enlarges fonts by 15%, hides debug, and shows a small step indicator ("Step 4 of 8: Objection loop") plus the talking point for the current step. **Demo Autopilot** calls the same public API as the buttons (no special code path) with short delays, so the autopilot is also a test.

---

# PART 7: TESTS (one per demo step, plus anti-fake)

**Backend (pytest)**

| Step | Test | Assertion |
| --- | --- | --- |
| 1 | `test_upload_chunking` | PDF and MD versions of C1 give identical clause IDs; PII entities tokenised before any LLM call |
| 2 | `test_applicability` | C1 has at least one Applicable; C2 all Not applicable with reasons; C4 injection ignored and logged |
| 3 | `test_gap_conflict` | C1 yields 1 gap and 1 conflict; Z3 returns a satisfying counter-example that, when evaluated against both rules, gives different actions |
| 4 | `test_objection_loop` | Iteration 1 rejected, 2 passes; iteration count never exceeds 3; the 4th would escalate to a human |
| 5 | `test_backtest_real` | Delta equals an independent DuckDB count; changing the threshold changes the result |
| 6 | `test_approval_security` | One signature, same user twice, and post-sign tampering are all rejected with 403 |
| 7 | `test_canary_sprt` | Healthy run reaches 100%; flood triggers breach through SPRT; `rollback_ms` equals measured time; previous bundle hash restored |
| 8 | `test_replay_and_tamper` | 20 replays match; one flipped byte fails `verify_chain` at the right index; Merkle inclusion proof verifies |
| all | `test_sse_order` | Events have increasing `seq`; resuming with `Last-Event-ID` loses nothing |

**Frontend (Playwright `e2e/demo.spec.ts`)**

The test drives the real UI through all 8 steps. It asserts that displayed values equal API values (for example, the hash shown in the Replay card equals `GET /audit/replay/{id}.recomputed_hash`), that the Deploy button stays disabled until both signatures exist, and that the rollback banner shows the same `rollback_ms` as the API. Run it twice back to back.

**Anti-fake CI (`scripts/no_fakes.sh`)**

Fail the build if `web/src`, `web/app` or the API routers contain any of:

- the strings `HASH MATCH`, `ROLLED BACK IN`, `divergence` next to a numeric literal, or a toast containing a digit literal;
- a hex literal of 32 or more characters;
- the words `sample_packet`, `mock`, `fake`, `hardcoded` outside `tests/` and `legacy/`;
- fixed result multipliers such as `* 0.04` in `services/agents/`.

---

# PART 8: PHASES AND PROMPTS

**R0: Triage (1 hour).** *"Create the branch `rebuild`. Move v1 fraud code to `legacy/`, delete `ui/` and the Vue `web/`, scaffold the Next.js app in `web/`, add `scripts/no_fakes.sh`, and generate `types.generated.ts` from the OpenAPI. Gate: `make up` boots API plus web; the home page renders from `/meta`."*

**R1: Backend truth, part 1.** *"Implement B1-B6 from Part 2. Gate: tests for steps 1-5 pass; C1 runs with a natural objection loop and a 500k backtest from DuckDB."*

**R2: Backend truth, part 2.** *"Implement B7-B14 from Part 2 including the tamper demo. Gate: tests for steps 6-8 pass; the chaos flood causes an SPRT-driven rollback with a measured time."*

**R3: Design system and shell.** *"Build Part 5: tokens, fonts, Sidebar, TopBar with the stage stepper, TruthBadge, EvidenceDrawer, PresenterHud, and the four-state panel wrapper. Gate: shell renders at 1440 and 1920 with no console errors."*

**R4: Pages.** *"Build the 9 pages in Part 6, one at a time, each wired to real API/SSE data. After each page, show a screenshot and the list of API calls it makes. Gate: every metric opens the evidence drawer."*

**R5: Verification.** *"Write e2e/demo.spec.ts and make the tests in Part 7 pass. Run the demo twice. Run no\_fakes.sh. Gate: all green."*

**R6: Demo polish.** *"Add Demo Autopilot, the talking-point HUD, record/replay LLM cache, a 90-second backup video script, README with an architecture diagram, and a `make demo` target. Gate: a cold start to the end of the demo takes under 6 minutes of wall time, with no manual fixes."*

---

# PART 9: THE NEW DEMO (5 minutes, now with the tamper moment)

| Time | Action | Proof visible on screen |
| --- | --- | --- |
| 0:00 | Drag C1 PDF into the Inbox | Clauses stream in; the Airlock counter shows tokenised entities |
| 0:40 | Open Obligations; flip to C2 | Applicable vs Not applicable with reasons |
| 1:10 | Rule Studio | Z3 counter-example banner (the exact transaction); the gap card |
| 1:45 | Agent Mesh | Packets fly; Validator rejects; amber loop; iteration 2 passes |
| 2:20 | Impact | 500,000 rows processed; the real before/after delta |
| 2:50 | Approvals | Deploy with one signature: real 403. Then maker and checker both sign |
| 3:20 | Rollout | Shadow overlay, canary ladder, SPRT chart |
| 3:50 | Chaos: `alert_flood` | SPRT crosses the bound, red flash, measured `rollback_ms` |
| 4:20 | Audit | Replay: original and recomputed hash match; then **Tamper demo**: one flipped bit turns the chain red at the exact index |

**Closing line:** *"Every number you saw was computed live and you could click any of them to see the event behind it."*

**Risk list**

- Z3, DuckDB and OPA must run offline, so test with Wi-Fi off.
- If Ollama is slow, enable the record/replay cache and keep the badge honest: it will read `replay_cache`.
- Keep the 90-second backup video, but never present it as live.
- Do not claim features you have not wired: if the A2A transport is in-process, say "signed A2A envelopes with verified signatures" and not "distributed microservices".
