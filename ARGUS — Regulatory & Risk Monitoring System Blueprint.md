# ARGUS — Regulatory & Risk Monitoring System

*Agentic Regulatory & Risk Guard with Unified Safety — project blueprint for SIDAZ Technologies*

## 1. Problem Statement and the One Big Idea

Banks lose the compliance and fraud game on four fronts at once:

1. **Alert fatigue.** Rule-based AML and fraud engines generate 90–95%+ false positives. Analysts burn most of their day closing noise.
2. **Regulation lag.** Circulars and master directions change; turning them into working controls takes weeks or months of manual interpretation.
3. **LLM distrust.** Banks cannot adopt LLMs because outputs are non-deterministic, hallucinated answers are unacceptable, and PII must never leave the perimeter.
4. **No memory.** Most systems judge each transaction or query in isolation. They forget the customer's history, past analyst decisions, and which rule version was in force at the time.

**The biggest problem in the domain is not detection. It is trust: nobody can safely let an AI make or explain a regulated decision.** Detection models exist; what is missing is a system whose decisions are deterministic, replayable, explainable, privacy-safe and auditable.

**Our one big idea: "Deterministic core, probabilistic edge."** Decisions (allow / hold / escalate / block) are made by versioned policy-as-code plus calibrated ML scores. LLMs are never the decision-maker. They only (a) read unstructured text, (b) draft explanations from verified evidence, and (c) propose new rules for a human to approve. Every LLM call passes through a PII-tokenising gateway and a citation verifier.

## 2. Scope: Two Use Cases on One Platform

|  | Use Case A: Regulatory Compliance Copilot | Use Case B: Fraud & Risk Monitoring |
| --- | --- | --- |
| Users | Compliance officers, ops staff, relationship managers | Fraud and AML analysts, risk heads |
| Input | Regulatory circulars (PDF/HTML), internal policies, staff queries | Transaction streams, customer profiles, sanctions lists |
| Positive case | "Is this KYC refresh compliant under current rules?" → grounded, cited answer | Genuine high-value customer transfer → passes with a clear reason |
| Negative case | Request to bypass KYC, leak a customer record, or misread a rule → refused and logged | Structuring, mule account, account takeover, prompt-injected narrative → flagged or blocked |
| Output | Answer + clause citations + rule diff + impact analysis | Decision + risk score + evidence graph + draft SAR/STR narrative |

Both use cases share the same gateway, memory, policy engine, agent mesh and audit ledger. That sharing is what makes this a platform and not two demos.

## 3. Landscape: Best Existing Solutions and Their Loopholes

### 3.1 Transaction monitoring and fraud

| Solution | Best features | Loopholes |
| --- | --- | --- |
| NICE Actimize, SAS AML, Oracle FCCM | Mature scenario libraries, case management, regulator-trusted, end-to-end workflow | Heavy and expensive, slow to change; static thresholds drive huge false-positive rates; weak real-time; LLM features are bolt-ons |
| Featurespace ARIC | Adaptive behavioural ML, strong real-time scoring | Proprietary black box; explanations are thin; no regulation-to-rule linkage |
| Feedzai, Sardine, Unit21 | Fast risk APIs, good UX, device and behavioural signals | API-call model: data leaves the bank's boundary; per-call pricing; limited customisation of policy logic |
| Hawk AI, Napier AI | AI-assisted alert triage, explainability dashboards | Closed stacks; "explainability" is post-hoc; memory of analyst feedback is limited |
| Open source: Marble, Jube, Tazama | Free, rule/decision engines, real-time capable, auditable | No LLM layer, no regulation ingestion, no agent interoperability, no privacy gateway, basic case UX |

### 3.2 Regulatory intelligence and compliance

| Solution | Best features | Loopholes |
| --- | --- | --- |
| Thomson Reuters Regulatory Intelligence, Wolters Kluwer | Authoritative content, change alerts | Alerts tell you *that* something changed, not *what to change in your controls* |
| CUBE, Regology, Ascent | Regulation mapping, obligation libraries | Mapping is largely manual or vendor-curated; obligations are not executable; no automatic test generation |
| Generic RAG copilots (LangChain + hosted LLM) | Fast to demo | Hallucinated citations; non-deterministic; PII sent to external LLM; no versioning ("which rule applied on 3 March?"); no refusal logic |

### 3.3 AI safety and memory tooling

| Tool | Best features | Loophole |
| --- | --- | --- |
| NeMo Guardrails, Llama Guard, Lakera | Prompt-injection and toxicity filters, programmable rails | Generic, not banking-aware; no PII tokenisation round-trip; no link to policy engine |
| Microsoft Presidio | Good PII detection and anonymisation | Detection only; does not provide reversible, scoped tokenisation or a leak-proof egress gate |
| Mem0, Zep, LangGraph checkpointers | Easy conversational memory | Memory is "what was said", not "what was decided under which rule version"; no bitemporal facts; no per-customer access control or erasure guarantees |
| Google A2A, Anthropic MCP | Open standards for agent discovery and tool access | Standards only: no trust model, no signed identities or per-skill authorisation for regulated settings |

### 3.4 Gap summary

No existing product combines: (1) executable, versioned regulation, (2) deterministic decisions with LLMs confined to the edge, (3) a PII-proof gateway, (4) decision-aware bitemporal memory, (5) secure agent-to-agent skills, and (6) cost-bounded inference. That intersection is where ARGUS sits.

## 4. Our Solution: ARGUS

### 4.1 Design principles

1. **Policy-as-code decides; models advise; LLMs explain.**
2. **Zero raw PII outside the vault.** The LLM sees only typed tokens such as `<ACCT_7F3A>`.
3. **Every answer is evidence-bound.** No verified citation or evidence ID means no output (the system abstains and escalates).
4. **Replay or it didn't happen.** Any past decision can be re-run bit-for-bit with the stored inputs, rule version, model version and seed.
5. **Cheapest sufficient tier.** Rules first, small model second, big model last; semantic cache in front.
6. **Human-in-the-loop by risk tier, not by default.** Low-risk is automated, high-impact needs two-person approval.

### 4.2 Key innovations (what makes it more than an API wrapper)

| # | Innovation | What it fixes |
| --- | --- | --- |
| 1 | **Reg-to-Rule Compiler.** Ingests a circular, extracts obligations into structured form, drafts Rego/YAML rule changes plus test cases, and shows an impact simulation against historical data. A human approves. | Regulation lag |
| 2 | **PII Airlock.** Detect → tokenise (format-preserving, scoped per session) → LLM → verify → detokenise only inside the vault boundary. Egress filter blocks any raw identifier. | PII leakage, external-LLM risk |
| 3 | **Evidence-Bound Generation.** Every claim must cite a clause ID or evidence node; a verifier checks claims against sources; failures abstain. | Hallucination |
| 4 | **Bitemporal Decision Memory.** Stores *valid time* and *recorded time* for facts, rules and decisions, so we can answer "what did we know and which rule applied when we decided?" Includes analyst feedback loops. | No memory, audit gaps |
| 5 | **Signed Agent Mesh.** A2A agent cards signed with Ed25519, per-skill scopes, MCP tools behind an authorising proxy, and full call tracing. | Unsafe multi-agent interaction |
| 6 | **Alert Compression.** Graph-linked alerts are clustered into one *case* with a ranked evidence story; an active-learning loop from analyst outcomes down-weights noisy rules. | Alert fatigue |
| 7 | **Cost Router.** Cascade: cache → rules → LightGBM → small local LLM → larger model; prompt compression; per-customer token budget with alarms. | Cost and latency |
| 8 | **Adversary Harness.** Automated red-team suite (prompt injection, PII exfiltration, mule-account behaviour simulation, rule-evasion) runs in CI and gates merges. | Bad users |

### 4.3 How determinism is achieved

- Decisions come from OPA policies plus fixed-version ML models with pinned thresholds. No sampling randomness in the decision path.
- LLM calls use temperature 0, fixed seed, constrained JSON output (schema-validated), pinned model digest.
- Each decision stores a **decision record**: input hash, rule bundle version, model version, evidence IDs, output hash. A `replay` command re-executes and compares hashes; CI fails on drift.
- Explanations are *templated first, LLM-polished second*, and the polished text must pass the citation verifier or the template is shown.

### 4.4 Human-in-the-loop tiers

| Tier | Example | Handling |
| --- | --- | --- |
| T0 | Routine query, low-value normal transaction | Fully automated, sampled QA |
| T1 | Medium risk, model-score borderline | Analyst review queue with pre-built case |
| T2 | Possible sanctions hit, large structuring pattern, new rule publication | Maker–checker (two humans), cannot auto-execute |
| T3 | SAR/STR filing, account freeze | Compliance officer sign-off, signed audit entry |

## 5. System Architecture

### 5.1 Logical architecture

```text
┌────────────────────────────── CLIENT / UI ───────────────────────────────┐
│  Streamlit: Analyst Console | Compliance Copilot | Rule Studio | Audit   │
└───────────────┬───────────────────────────────────────────────────────────┘
                │ HTTPS (OIDC / JWT, RBAC)
┌───────────────▼──────────────── API GATEWAY (FastAPI) ───────────────────┐
│  AuthN/Z → Rate limit → Request ID → Tracing (OpenTelemetry)             │
└───────┬───────────────────────────────────────────────────────┬──────────┘
        │                                                       │
┌───────▼──────────┐   ┌───────────────────────────┐   ┌───────▼──────────┐
│  PII AIRLOCK     │   │  ORCHESTRATOR (LangGraph) │   │  EVENT BACKBONE  │
│  Presidio+regex  │──▶│  state machine, retries,  │◀──│  Redpanda/NATS   │
│  tokeniser/vault │   │  HITL interrupts          │   │  txn + case bus  │
└───────┬──────────┘   └──────┬──────────┬─────────┘   └──────────────────┘
        │                     │          │
        │           ┌─────────▼───┐  ┌───▼─────────────────────────┐
        │           │ POLICY      │  │ AGENT MESH (A2A + MCP)      │
        │           │ ENGINE (OPA)│  │  Reg-Intel Agent            │
        │           │ versioned   │  │  Txn-Risk Agent             │
        │           │ bundles     │  │  KYC/Sanctions Agent        │
        │           └─────────┬───┘  │  Investigator Agent         │
        │                     │      │  Narrative (SAR) Agent      │
        │                     │      └───┬─────────────────────────┘
┌───────▼─────────────────────▼──────────▼───────────────────────────────┐
│                        COGNITION SERVICES                              │
│  Cost Router → Semantic Cache → LightGBM+SHAP → Ollama (local LLM)     │
│  Evidence Verifier | Guardrails (Llama Guard / NeMo) | Prompt compressor│
└───────┬───────────────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────── DATA & MEMORY ─────────────────────────┐
│ PostgreSQL 16: transactions, cases, bitemporal memory, audit ledger    │
│ pgvector: regulation + case embeddings   | Redis: cache, rate, sessions│
│ MinIO: documents | Graph view: Postgres recursive CTE / NetworkX (MVP) │
│ Vault (tokens ↔ PII), encrypted, separate schema and credentials       │
└───────────────────────────────────────────────────────────────────────┘
        ▲
        └── Observability: Langfuse (self-host), Prometheus, Grafana, Loki
```

### 5.2 Request flow (Use Case B: suspicious transaction)

1. Transaction arrives on the event bus → features computed (velocity, device, counterparty graph hops).
2. **Policy engine** evaluates hard rules (sanctions, limits, structuring windows) → immediate T2/T3 routes if hit.
3. **LightGBM** score + SHAP attributes → risk band.
4. If borderline, **Investigator Agent** pulls bitemporal memory (customer history, previous analyst outcomes) and the counterparty subgraph.
5. **PII Airlock** tokenises case text → local LLM drafts explanation from evidence → **Evidence Verifier** checks → detokenise inside the vault boundary for the analyst view.
6. Case lands in the Analyst Console with decision, evidence, rule version, and HITL tier. Analyst outcome feeds back to memory and rule-weight tuning.
7. Decision record + hash is appended to the **audit ledger** (hash-chained).

### 5.3 Request flow (Use Case A: compliance query or new circular)

1. Query/circular enters the Airlock → classified (query, change-ingest, or attack).
2. Hybrid retrieval (BM25 + pgvector) over versioned regulation corpus, filtered by *valid-time* ("as of date").
3. Answer assembled with clause citations; verifier rejects uncited claims; unanswerable → abstain + escalate.
4. For a new circular: Reg-to-Rule Compiler produces obligation JSON → draft rule + tests → impact simulation on historical transactions → maker–checker approval → OPA bundle published with a new version.

### 5.4 Agent-to-Agent design

- Each agent publishes an **A2A Agent Card** (name, skills, input/output schema, auth scheme) and is signed.
- Skills are narrow and typed, e.g. `risk.score_transaction`, `reg.explain_clause`, `kyc.check_sanctions`, `case.draft_narrative`.
- A **capability broker** enforces which agent may call which skill with which data class (tokens only, never raw PII).
- External tools (sanctions API, document store) are exposed over **MCP** behind the same broker.
- Every agent call is traced end to end with the case ID.

### 5.5 Memory layer

| Layer | Contents | Tech |
| --- | --- | --- |
| Working | Current case/conversation state | LangGraph checkpointer (Postgres) |
| Episodic | Past interactions, analyst decisions and rationales | Postgres, bitemporal tables (valid\_from/valid\_to, recorded\_at) |
| Semantic | Customer behavioural profile, regulation corpus | pgvector + structured columns |
| Procedural | Rule versions, playbooks, learned rule weights | OPA bundles in Git + weight table |
| Governance | Retention, consent, right-to-erase, purpose limitation | Policy tags on every row; erase = tombstone + crypto-shred keys |

Mem0 OSS can be used for the conversational extraction layer, but the authoritative store is our own Postgres schema so that time-travel queries and erasure are guaranteed.

## 6. Threat Model (Bad Users and Exploits)

| Threat | Mitigation |
| --- | --- |
| Prompt injection via customer text, document, or transaction narrative | Input rails (Llama Guard + pattern rules), content treated as data in a delimited slot, LLM has no tool power outside brokered skills |
| PII exfiltration ("print the customer's Aadhaar/PAN") | Airlock tokenisation, egress regex + entropy gate, role-based detokenisation, refusal policy |
| Model/Agent impersonation | Signed agent cards, mTLS between services, short-lived JWTs |
| Rule evasion (structuring, smurfing, mule rings) | Graph features, multi-window velocity, adversary simulator in CI |
| Insider misuse | Maker–checker, immutable audit chain, anomaly detection on analyst behaviour |
| Data poisoning of feedback loop | Feedback needs reviewer role, outlier filter, rollback of rule-weight versions |
| Replay/forgery of audit data | Hash-chained ledger, periodic root hash export |
| Cost-abuse (token flooding) | Per-user and per-customer budgets, size limits, cache, backpressure |

## 7. Technology Stack (Open Source / Free Tier)

| Layer | Choice | Why |
| --- | --- | --- |
| Language | Python 3.12 (services), TypeScript optional later | Ecosystem for ML and agents |
| API | FastAPI + Pydantic v2 | Typed schemas, async, OpenAPI |
| Orchestration | LangGraph | Stateful graphs, interrupts for HITL, checkpointing |
| Agent protocols | `a2a-sdk` (Google A2A), MCP Python SDK | Open standards |
| Policy engine | Open Policy Agent (Rego) | Versioned policy bundles, unit-testable, deterministic |
| ML | LightGBM / XGBoost + SHAP, scikit-learn, NetworkX | Fast, explainable, CPU-friendly |
| LLM runtime | Ollama with Qwen2.5-7B / Llama-3.1-8B (local); optional free-tier hosted model only for non-PII tasks | Privacy and zero per-token cost |
| Embeddings | `bge-small` / `nomic-embed-text` (local) | Free, small |
| PII | Presidio + custom Indian identifier recognisers (PAN, Aadhaar, IFSC, UPI) | Extensible |
| Guardrails | Llama Guard 3 (local), NeMo Guardrails, custom verifier | Layered |
| Data | PostgreSQL 16 + pgvector, Redis, MinIO | One database for relational, vector, and temporal needs |
| Streaming | Redpanda Community or NATS JetStream | Lightweight Kafka-compatible bus |
| Observability | OpenTelemetry, Langfuse (self-hosted), Prometheus, Grafana | Traces of every LLM and agent call |
| Security | Keycloak (OIDC), HashiCorp Vault OSS or `cryptography`+KMS-style wrapper, Ed25519 signing | Realistic bank-grade patterns |
| Testing | pytest, Hypothesis, promptfoo, garak, OPA `test` | Property, adversarial and policy tests |
| UI | Streamlit (multipage) | Required mock UI |
| DevOps | Docker Compose (MVP), Helm/K3s (stretch), GitHub Actions, pre-commit, Ruff, mypy | Reproducible |
| Datasets | IBM AML synthetic transactions, PaySim, ULB credit-card fraud, OpenSanctions (open data), public RBI/FATF documents | Free and realistic |

## 8. Repository and Folder Structure

```text
argus/
├── README.md                      # problem, architecture, quickstart, demo GIFs
├── docs/
│   ├── architecture/              # C4 diagrams (Mermaid/PlantUML), ADRs
│   ├── threat-model.md
│   ├── api/                       # OpenAPI export
│   └── runbooks/
├── deploy/
│   ├── docker-compose.yml
│   ├── helm/                      # stretch
│   └── env.example
├── policies/                      # policy-as-code (Rego) — versioned bundles
│   ├── aml/ fraud/ kyc/ privacy/
│   └── tests/                     # opa test cases
├── services/
│   ├── gateway/                   # FastAPI entrypoint, auth, rate limits
│   ├── airlock/                   # PII detect/tokenise/vault/egress gate
│   ├── orchestrator/              # LangGraph graphs, HITL interrupts
│   ├── agents/
│   │   ├── reg_intel/ txn_risk/ kyc_sanctions/ investigator/ narrative/
│   │   └── common/                # agent card, signing, A2A server/client
│   ├── broker/                    # capability broker, MCP proxy
│   ├── cognition/
│   │   ├── router/                # cost router, budgets
│   │   ├── cache/                 # semantic cache
│   │   ├── verifier/              # evidence/citation verifier
│   │   └── models/                # LightGBM training + registry
│   ├── memory/                    # bitemporal store, episodic/semantic APIs
│   ├── regcompiler/               # circular → obligations → rules + tests
│   ├── ledger/                    # hash-chained audit + replay
│   └── ingest/                    # txn simulator, stream consumers
├── ui/                            # Streamlit pages: console, copilot, studio, audit
├── ml/                            # notebooks, feature definitions, eval reports
├── redteam/                       # promptfoo/garak configs, attack corpora, mule simulator
├── tests/                         # unit, integration, contract, determinism/replay
├── data/                          # scripts to fetch datasets (no raw data committed)
├── scripts/                       # seed, replay, benchmark
├── .github/workflows/             # lint, test, opa-test, redteam, build
└── pyproject.toml
```

Architectural conventions: hexagonal (ports and adapters) per service, one Pydantic schema package shared as `contracts/`, ADRs for every major decision, no service imports another service's internals (only contracts or A2A calls).

## 9. Data Model Highlights

- `transactions(id, account_token, counterparty_token, amount, ts, channel, device_id_token, …)`
- `decisions(id, input_hash, rule_bundle_ver, model_ver, score, outcome, tier, evidence_ids[], output_hash, recorded_at)`
- `facts(subject, predicate, object, valid_from, valid_to, recorded_at, source, classification)` — bitemporal
- `regulation_clauses(id, doc_id, version, text, valid_from, valid_to, embedding)`
- `obligations(id, clause_id, actor, condition_json, action_json, rule_ref)`
- `audit_ledger(seq, prev_hash, payload_hash, signer, ts)` — append-only
- `pii_vault(token, kind, ciphertext, scope, expires_at)` — separate schema and DB role

## 10. Phase-by-Phase MVP Plan

Assumes a small team (3–4 people) and roughly 6–8 weeks. Compress for a hackathon by doing Phases 0–3 plus a thin slice of 4.

### Phase 0 — Foundations (Week 1)

- Repo, CI, pre-commit, Docker Compose with Postgres+pgvector, Redis, OPA, Ollama, Redpanda.
- Contracts package, ADR-001 (deterministic core), threat model v0.
- Synthetic transaction generator (normal, structuring, mule ring, account-takeover) + dataset loaders.
- **Exit:** `docker compose up` brings up the stack; sample transactions flow into Postgres.

### Phase 1 — Privacy and Policy Core (Weeks 1–2)

- PII Airlock: Presidio + Indian recognisers, tokeniser, vault, egress gate, tests with leak corpus.
- OPA policies for 10–15 rules (sanctions hit, structuring windows, velocity, geo/device anomaly, KYC expiry) with unit tests.
- Hash-chained audit ledger and `replay` CLI.
- **Exit:** a transaction produces a deterministic decision record that replays identically; zero PII in any LLM-bound payload (asserted in tests).

### Phase 2 — Risk Intelligence (Weeks 2–3)

- Feature pipeline (velocity, graph hops, device sharing) and LightGBM model with SHAP.
- Cost Router with cache and budgets; calibrated thresholds.
- Case clustering: link alerts sharing counterparties/devices into one case.
- **Exit:** benchmark shows target precision/recall and alert-volume reduction versus a rules-only baseline.

### Phase 3 — Memory and Agents (Weeks 3–5)

- Bitemporal memory service and analyst-feedback loop.
- LangGraph orchestrator with HITL interrupts by tier.
- Agent mesh: Txn-Risk, KYC/Sanctions, Investigator, Narrative agents with signed A2A cards and capability broker; one MCP tool (sanctions lookup).
- Evidence Verifier and constrained local-LLM explanations.
- **Exit:** a borderline transaction triggers multi-agent investigation, produces a cited narrative, waits for analyst approval, and the outcome changes future scoring.

### Phase 4 — Regulatory Copilot and Reg-to-Rule Compiler (Weeks 5–6)

- Ingest 5–10 public circulars/directions; clause chunking with versioning and valid-time.
- Cited Q&A with abstention; "as of date" queries.
- Compiler: circular → obligations JSON → draft Rego + test cases → impact simulation → maker–checker publish.
- **Exit:** demo of a new circular producing a reviewed rule change with before/after alert impact.

### Phase 5 — Hardening, UI and Submission (Weeks 6–8)

- Streamlit console (alert queue, case view with evidence graph, copilot chat, rule studio, audit viewer, cost dashboard).
- Red-team harness in CI, load and latency benchmarks, token/cost report per customer.
- README, C4 diagrams, ADRs, demo script, short video.
- **Exit:** all acceptance metrics met; clean clone-to-demo in under 10 minutes.

## 11. Acceptance Metrics (What We Will Measure and Show)

| Metric | Target for MVP |
| --- | --- |
| PII leakage into LLM payloads | 0 across the adversarial corpus |
| Decision determinism (replay hash match) | 100% |
| Citation validity (claims with verified source) | ≥ 98%; the rest abstain |
| Alert volume vs. rules-only baseline at equal recall | 40–60% reduction (to be validated on synthetic and public data) |
| Prompt-injection block rate (red-team suite) | ≥ 95%, with remaining cases failing safe |
| p95 latency, T0 decision | < 300 ms without LLM; < 3 s with local LLM explanation |
| LLM tokens per case | Budgeted; ≥ 60% fewer than naive full-context RAG baseline |
| Cost per 1,000 decisions | Reported and compared to a hosted-LLM baseline |

The numeric targets above are goals to validate, not claims; report whatever the benchmarks actually show.

## 12. Token and Inference Optimisation Details

- **Tiered execution:** most events never touch an LLM; only borderline or text-heavy items do.
- **Semantic cache** keyed by tokenised-query embedding plus rule-bundle version (so cache never serves answers from an outdated rule version).
- **Structured context packing:** send evidence IDs and short fact tuples, not raw documents; prompt compression for long clauses.
- **Small-first routing:** 7–8B local model for explanation; escalate only on verifier failure.
- **Batching and async:** narrative drafts generated off the hot path.
- **Budgets:** per-customer and per-analyst token ceilings with dashboards and alerts.

## 13. Why This Makes a Real Impact

| Stakeholder | Impact |
| --- | --- |
| Analysts | Fewer alerts, each arriving as a ranked, evidence-linked case with a draft narrative; less time on noise |
| Compliance heads | Regulation changes become reviewed, tested rule updates in days instead of months; clear "as of date" answers |
| Auditors and regulators | Every decision is replayable and attributable to a rule version, model version and approver |
| CISOs and DPOs | No PII leaves the perimeter; erase and consent controls built into memory |
| CFO / Ops | Local-first inference and tiered routing reduce per-decision cost versus per-call vendor APIs |
| Smaller banks, co-operatives and NBFCs | An open, self-hostable alternative to costly enterprise suites |

**Differentiation in one line:** others bolt an LLM onto a rules engine; ARGUS makes the rules engine the authority and uses the LLM as a supervised, privacy-wrapped assistant, with memory and replay that make the whole thing auditable.

## 14. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Scope too large | Strict phase gates; ship Use Case B vertical slice first, A as second slice |
| Small local LLM quality | Template-first explanations, verifier, optional free-tier hosted model on tokenised, non-PII text only |
| Synthetic data realism | Use IBM AML and PaySim plus adversarial simulator; be explicit about limits |
| Compiler producing wrong rules | Never auto-publish; tests + impact simulation + maker–checker |
| Compliance-claim overreach | Describe as "supports" and "designed for" compliance; no claim of regulatory certification |

## 15. README and Submission Checklist

- Problem and one-big-idea summary, architecture diagram (C4 level 1–3), data-flow diagrams.
- Quickstart (`make up`, `make seed`, `make demo`), screenshots/GIFs of Streamlit UI.
- Design decisions (ADRs), threat model, benchmark report, cost report.
- How to run replay and red-team suites.
- Licence (Apache-2.0 suggested), contribution guide, known limitations.

## 16. Demo Script (5 Minutes)

1. **Bad user:** prompt-injected transaction narrative asking to reveal an account holder's PAN → blocked, logged, shown in the audit viewer.
2. **Good flow:** normal high-value transfer from a long-standing customer → auto-approved with a clear reason.
3. **Suspicious ring:** structuring across linked accounts → one clustered case, evidence graph, draft STR narrative, analyst approves.
4. **Memory:** same customer later → system references the earlier decision and the rule version in force then.
5. **New circular:** upload → obligations → draft rule → impact simulation → maker–checker publish.
6. **Replay:** re-run an old decision and show the identical hash; show cost per 1,000 decisions.

## 17. Immediate Next Steps

1. Confirm target geography/regulations (e.g., India: RBI KYC and PMLA-related directions, DPDP Act) to pick the initial corpus.
2. Freeze the MVP rule list (10–15 rules) and the 3 attack scenarios.
3. Create the repo skeleton from Section 8 and the Docker Compose stack (Phase 0).
4. Decide team split: policy/ML, airlock/security, agents/orchestration, UI/DevOps.

*Suggested follow-ups: I can generate the repo skeleton, the Docker Compose file, the first OPA policies, the Airlock service, or the LangGraph orchestrator code, one phase at a time.*
