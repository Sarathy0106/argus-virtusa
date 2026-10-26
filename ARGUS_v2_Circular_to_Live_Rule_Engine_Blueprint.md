# ARGUS v2 — Regulatory Circular to Live Rule Engine

*Agentic Regulatory Guard with Unified Safety. Blueprint re-aligned to FDS NA Use Case 2.*

---

## 0. Alignment Audit (why v1 was revised)

**Verdict on v1: partially aligned, not a direct solution for Use Case 2.** It had the right ideas (Reg-to-Rule Compiler, PII Airlock, evidence-bound output, signed agent mesh) but split its effort across two use cases, and Use Case B (fraud/AML monitoring) is not in the brief.

| Use Case 2 requirement | v1 status | Fix in v2 |
| --- | --- | --- |
| Scope: circular → live rule engine only | ❌ Half the document was fraud/AML monitoring | Fraud scope removed. Historical transactions are now only a *backtest data source* |
| Stage 1 Circular Intake | ✅ Present | Kept, now a dedicated Intake Agent |
| Stage 2 Obligation Extraction + **applicability** | ⚠️ No applicability check against the bank profile | Obligation Agent adds applicability determination (bank profile, products, licence type) |
| Stage 3 **Policy Mapping** to internal policies and existing system rules | ❌ Missing | New Policy Mapper Agent: gap, overlap and conflict detection |
| Stage 4 Rule Authoring | ✅ Present | Kept; rules authored in a Rule DSL, compiled to the target engine |
| Stage 5 Backtesting | ⚠️ Merged with impact | Separate stage with its own agent and sandbox |
| Stage 6 Impact Analysis | ⚠️ Merged | Separate Impact Agent: volume, segments, false positives, ops load |
| Stage 7 **Validation** | ❌ Missing as a gate | Validator Agent with objection loop back to stages 3–4 |
| Stage 8 Human Approval | ✅ Present | Kept as a maker–checker gate |
| Stage 9 **Shadow Deployment** | ❌ Missing | New: parallel evaluation, no enforcement |
| Stage 10 **Rollout, Monitoring, Rollback** | ❌ Missing | New: canary ramp, drift monitors, automatic rollback |
| Multi-agent collaboration via A2A, iterative issue resolution | ⚠️ One Reg-Intel agent only | Eight specialised agents plus orchestrator that re-routes on objections |
| Data sources: bank profiles, rule repositories, deployment metrics, approval history | ⚠️ Partial | All added |
| Guardrails: draft-only, clause-level traceability, rollback, rate limits | ⚠️ Rollback missing | All present and enforced in code |

**Kept from v1 because it strengthens Use Case 2:** PII Airlock, Evidence-Bound Generation, Signed Agent Mesh, Bitemporal Memory (answers "which rule applied on date X"), hash-chained audit ledger, Cost Router.

---

## 1. Problem and One Big Idea

**Problem.** Banks interpret regulatory circulars by hand, map them to internal policies and live system rules, then coordinate with IT. This takes weeks or months, risks missing obligations, and can ship rules with the wrong scope or unexpected transaction impact.

**Big idea: "Circular in, safe rule out."** Every circular passes through ten gated stages. Agents *draft*, deterministic code *validates*, humans *approve*, and the rule goes live only through shadow mode and a monitored, reversible rollout. LLMs never publish anything.

## 2. Workflow (exactly as specified in the use case)

Circular Intake → Obligation Extraction → Policy Mapping → Rule Authoring → Backtesting → Impact Analysis → Validation → Human Approval → Shadow Deployment → Rollout & Monitoring

| # | Stage | Agent | Output |
| --- | --- | --- | --- |
| 1 | Circular Intake | Intake Agent | Clause-chunked, versioned circular with valid-time; PII-airlocked |
| 2 | Obligation Extraction | Obligation Agent | Obligation registry entries (actor, condition, action, deadline) and an applicability verdict for this bank |
| 3 | Policy Mapping | Policy Mapper Agent | Obligation → internal policy clause and existing rule map; gaps, overlaps, conflicts |
| 4 | Rule Authoring | Rule Author Agent | Draft rule change in Rule DSL, plus test cases (draft-only) |
| 5 | Backtesting | Backtest Agent | Draft vs current rule run over historical transactions in the sandbox |
| 6 | Impact Analysis | Impact Agent | Alert/decline volume delta, affected segments, false-positive and ops-load estimate |
| 7 | Validation | Validator Agent | Pass/fail on schema, conflicts, clause coverage, citations; objections routed back to stage 3 or 4 |
| 8 | Human Approval | Approval workflow (humans) | Maker–checker decision with signed audit entry |
| 9 | Shadow Deployment | Deployment Agent | New rule runs in parallel on live traffic, logged but not enforced |
| 10 | Rollout & Monitoring | Monitor Agent | Canary ramp, drift and impact monitors, automatic rollback |

**Why agentic.** Agents exchange findings and objections over A2A. Example: the Validator finds a rule that conflicts with an existing limit, so the Orchestrator re-routes to the Policy Mapper and Rule Author, and the flow resumes with the new evidence. A fixed pipeline cannot do this.

## 3. Key Innovations

1. **Obligation Registry.** Executable, versioned obligations, each linked to its source clause.
2. **Applicability Engine.** Filters circulars against the bank profile so teams only act on what applies.
3. **Policy-to-Rule Traceability Graph.** Clause → obligation → policy → rule → test, queryable end to end.
4. **Objection Loop.** Validator and Impact agents can reject a draft; the Orchestrator re-routes with a bounded iteration limit.
5. **Shadow-First Deployment.** No rule enforces before its shadow-mode behaviour matches the backtest within tolerance.
6. **Reversible Rollout.** Every rule version is a Git-tagged bundle; rollback is a one-step pointer change.
7. **PII Airlock and Evidence Verifier.** Tokenised LLM inputs; uncited claims are rejected and escalated.
8. **Signed Agent Mesh.** Signed A2A agent cards, per-skill scopes, MCP tools behind an authorising proxy.

## 4. Architecture

```text
UI (Streamlit): Circular Inbox | Obligation Map | Rule Studio | Impact Report | Approvals | Rollout Monitor | Audit
        │  OIDC / JWT, RBAC
API Gateway (FastAPI): authN/Z, rate limits, request ID, OpenTelemetry
        │
PII Airlock ──► ORCHESTRATOR (LangGraph) ◄──► Capability Broker (A2A + MCP)
                state machine, retries, HITL interrupts, objection routing
                        │
   ┌────────────────────┴──────────────── AGENT MESH (signed A2A) ───────────────────────┐
   │ Intake → Obligation → Policy Mapper → Rule Author → Backtest → Impact → Validator    │
   │                                                    Deployment → Monitor              │
   └──────────────────────────────────────────────────────────────────────────────────────┘
        │
Cognition: Cost Router → Semantic Cache → Ollama local LLM → Evidence/Citation Verifier → Guardrails
        │
Execution: Rule DSL compiler → Sandbox engine (OPA) → Backtest runner → Shadow/Canary controller → Deployment API (mock core rule engine)
        │
Data: Postgres 16 (+ pgvector, bitemporal tables, audit ledger) | Redis | MinIO | Git rule repo | PII vault
Observability: Langfuse, Prometheus, Grafana
```

## 5. Data Sources

Regulatory circulars (public RBI and similar documents), internal policies, rule repositories, bank profiles, historical transaction data (synthetic and public datasets such as PaySim and the IBM AML set), backtest results, deployment metrics, approval history.

## 6. Technology Stack

| Layer | Choice |
| --- | --- |
| Multi-agent orchestration | LangGraph (stateful graph, HITL interrupts, checkpointing) |
| Agent messaging | Google A2A (`a2a-sdk`), MCP Python SDK |
| Document retrieval | pgvector + BM25 hybrid, `bge-small` embeddings, valid-time "as of" filter |
| Obligation registry | PostgreSQL, JSON schema, clause IDs |
| Rule DSL and engine | YAML Rule DSL compiled to Rego, evaluated by Open Policy Agent |
| Sandbox and backtesting | Isolated OPA instance, replay runner, pandas/DuckDB for metrics |
| Version control | Git rule repository, signed tags per bundle |
| Deployment APIs | FastAPI mock core rule-engine API: shadow, canary, promote, rollback |
| Monitoring | OpenTelemetry, Prometheus, Grafana, Langfuse |
| LLMs | Ollama (Qwen2.5-7B / Llama-3.1-8B) behind the PII Airlock; larger model only on verifier failure |
| Security | Keycloak, Ed25519 signing, mTLS, Vault OSS |
| UI and DevOps | Streamlit, Docker Compose, GitHub Actions, pytest, promptfoo |

## 7. Guardrails (enforced in code, not prompts)

- **Draft-only:** agents can create drafts; only the Deployment API with a valid dual approval token can change live rules.
- **Clause-level traceability:** each rule and test links to the clause that caused it.
- **Validation gate:** schema, conflict, coverage and citation checks must pass before approval is possible.
- **Mandatory human approval:** maker–checker; two people for high-impact rules.
- **Controlled rollout:** shadow, then canary (for example 1% → 10% → 50% → 100%), each step gated on live metrics.
- **Automatic rollback:** breach of impact or latency thresholds reverts to the previous bundle version.
- **Rate, iteration and token limits** on every agent loop and LLM call.
- **Prompt-injection defence:** circular text is data in a delimited slot; agents have no tool access outside brokered skills.
- **Replay:** every decision stores input hash, rule version, model version and evidence IDs in a hash-chained ledger.

## 8. Memory

| Layer | Content |
| --- | --- |
| Working | Current case state (LangGraph checkpointer) |
| Episodic | Past circulars, reviewer decisions and rationales, approval history |
| Semantic | Regulation corpus, policy library, rule descriptions |
| Procedural | Rule versions, playbooks, rollout templates |
| Governance | Retention, erasure (tombstone plus key shredding), purpose limits |

Bitemporal storage answers "what did we know, and which rule version was live, when we decided?"

## 9. Threats and Mitigations

| Threat | Mitigation |
| --- | --- |
| Malicious or misleading text inside a circular | Input rails, treat as data, validator cross-check |
| Agent impersonation | Signed cards, mTLS, short-lived tokens |
| Wrong rule scope or hallucinated obligation | Evidence verifier, backtest, impact analysis, maker–checker |
| Rule change bypassing approval | Deployment API accepts only signed approval tokens |
| Insider misuse | Dual control, immutable audit chain |
| Runaway agent loops / cost abuse | Iteration, token and rate limits; budget alarms |

## 10. Phased MVP Plan (hackathon-compressed)

| Phase | Deliverable |
| --- | --- |
| 0 Foundations | Docker Compose stack, contracts package, synthetic transactions, sample rule repo |
| 1 Intake and Obligations | Clause chunking, Airlock, obligation registry, applicability check |
| 2 Mapping and Authoring | Policy mapper, Rule DSL → Rego compiler, test generation |
| 3 Evaluation | Sandbox, backtest runner, impact report, Validator with objection loop |
| 4 Governance and Release | Maker–checker UI, mock deployment API, shadow mode, canary and rollback |
| 5 Hardening | Red-team suite, replay CLI, dashboards, demo script |

## 11. Acceptance Metrics (targets to validate, not claims)

| Metric | Target |
| --- | --- |
| Circular → approved draft rule, time | Hours instead of weeks (measured on sample circulars) |
| Obligations with a valid clause citation | ≥ 98%; the remainder abstain and escalate |
| Replay hash match | 100% |
| Unapproved rule reaching enforcement | 0 |
| Rollback time after threshold breach | Under 1 minute in the demo |
| PII in LLM payloads | 0 across the adversarial corpus |

## 12. Enterprise Impact

Faster regulatory implementation, fewer compliance gaps, less manual effort, full clause-to-rule traceability, and safer rule deployment through shadow mode and reversible rollout.

## 13. Demo Script (5 minutes)

1. Upload a sample circular, which is parsed and clause-chunked.
2. Obligations are extracted and marked applicable or not for this bank.
3. Mapping shows one gap and one conflict with an existing rule.
4. Validator rejects the first draft; the Orchestrator re-routes; a corrected rule passes.
5. Backtest and impact report show before/after alert volumes.
6. Maker–checker approves; shadow mode runs on live traffic.
7. Canary ramps; a forced threshold breach triggers automatic rollback.
8. Audit viewer replays the decision with an identical hash.
