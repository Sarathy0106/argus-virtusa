# ARGUS — Agentic Regulatory & Risk Guard with Unified Safety

> *"Deterministic core, probabilistic edge."*  
> Decisions are made by versioned policy-as-code plus calibrated ML scores; LLMs explain and draft under strict PII airlocking and evidence-bound citation verification.

---

## 1. The Core Architecture

```text
┌───────────────────────────────── CLIENT / UI ──────────────────────────────────┐
│  Streamlit Console | Compliance Copilot | Rule Studio | Audit & Replay Explorer│
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       │ HTTPS / JSON API
┌──────────────────────────────────────▼─────────────────────────────────────────┐
│                    API GATEWAY & CAPABILITY BROKER (FastAPI)                   │
│  - Ed25519 Signed Agent Mesh (Txn-Risk, Sanctions, Investigator, Narrative)    │
│  - PII Airlock: Presidio + Indian Recognizers + Format-Preserving Vault        │
└──────────────┬─────────────────────────────────────────────────┬───────────────┘
               │                                                 │
┌──────────────▼──────────────┐                   ┌──────────────▼───────────────┐
│  POLICY ENGINE (OPA / Rego) │                   │      COGNITION & ML LAYER    │
│  - Versioned Git Bundles    │                   │  - Calibrated LightGBM Scorer│
│  - AML, Fraud, Sanctions    │                   │  - TreeSHAP Feature Attrib   │
│  - Bit-for-bit Determinism  │                   │  - Evidence Verifier Gate    │
└──────────────┬──────────────┘                   └──────────────┬───────────────┘
               │                                                 │
┌──────────────▼─────────────────────────────────────────────────▼───────────────┐
│                      DATA, BITEMPORAL MEMORY & AUDIT LEDGER                    │
│  - PostgreSQL 16 + pgvector | Redis Cache | SHA-256 Hash-Chained Audit Ledger  │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Innovations

| # | Innovation | What it solves | Implementation |
|---|---|---|---|
| 1 | **Deterministic Replay** | AI hallucinations & regulatory audit failure | Decisions stored with `input_hash` and `output_hash`. Replay engine confirms 100% bit-for-bit identity. |
| 2 | **PII Airlock** | PII leak risk into LLMs | Presidio + Indian recognizers (PAN, Aadhaar, IFSC, UPI) tokenizes data with AES-256-GCM. Strict egress gate terminates raw leaks. |
| 3 | **Evidence-Bound Explanations** | LLM hallucinations | Every narrative statement must cite `[EVID:<ID>]` or `[CLAUSE:<ID>]`. Uncited claims trigger deterministic template fallback. |
| 4 | **Bitemporal Memory** | Compliance time lag & lost context | Facts stored with `valid_from`, `valid_to` and `recorded_at` for "as-of-date" time travel and right-to-erase compliance. |
| 5 | **Signed Agent Mesh** | Multi-agent impersonation | Ed25519 cryptographic signatures on every A2A call behind a capability broker with tokens-only data boundaries. |
| 6 | **Alert Compression** | AML analyst alert fatigue | Graph-linked alerts (NetworkX) clustered into unified multi-transaction Cases (60% alert volume reduction). |
| 7 | **Cost Router** | Expensive LLM inference costs | Cascade: Cache $\to$ OPA Rules $\to$ LightGBM $\to$ Local LLM with per-customer daily token ceilings. |
| 8 | **Reg-to-Rule Compiler** | Regulation implementation lag | Ingests circulars, synthesizes Rego code + tests, simulates historical impact, and publishes via Maker-Checker. |

---

## 3. Quickstart & Walkthrough

### Prerequisites
- Python 3.12+
- Docker & Docker Compose (optional for full containerized stack)

### 1. Bootstrap Environment
```bash
# Auto-generate cryptographically secure keys (Vault AES-256, JWT, Tokenizer Salt)
python scripts/bootstrap_env.py
```

### 2. Run All Unit & Adversarial Tests
```bash
python -m pytest tests/unit/
```
*Executes all 53 unit, policy, replay, and red-team tests.*

### 3. Run the End-to-End Walkthrough Demo
```bash
python scripts/demo.py
```
*Walks through the complete 6-stage demo:*
1. Prompt injection attack blocked.
2. Routine transfer auto-approved.
3. Structuring & mule ring clustered into 1 unified case.
4. Bitemporal memory time-travel query.
5. Ingest circular $\to$ compile Rego $\to$ simulate historical impact.
6. Bit-for-bit replay hash verification.

### 4. Launch the Interactive Analyst Console
```bash
python -m streamlit run ui/app.py
```
*Opens the 5-page console:*
- **Page 1:** Analyst Case Queue & Maker-Checker Signoff
- **Page 2:** Regulatory Compliance Copilot with As-Of Date filtering
- **Page 3:** Rule Studio & Historical Impact Simulator
- **Page 4:** Hash-Chained Audit Ledger & Replay Explorer
- **Page 5:** Cost Router & Token Telemetry Dashboard

---

## 4. Phase-by-Phase Implementation Status

- ✅ **Phase 0: Foundations & Reproducible Environment** (Contracts, Docker stack, Simulator, ADR-001, Threat Model)
- ✅ **Phase 1: Privacy Airlock, Policy Engine & Deterministic Replay** (Presidio + Indian PII, 12 OPA rules, Hash-chained ledger)
- ✅ **Phase 2: Risk Intelligence, ML Scoring & Cost Router** (Feature pipeline, LightGBM, Semantic cache, Alert clustering)
- ✅ **Phase 3: Bitemporal Memory, Signed Agent Mesh & LangGraph Orchestration** (Bitemporal store, Ed25519 mesh, Verifier, HITL)
- ✅ **Phase 4: Regulatory Copilot & Reg-to-Rule Compiler** (Corpus indexing, BM25 temporal search, Rego compiler, Simulator)
- ✅ **Phase 5: Analyst Console UI, Adversarial Red-Teaming & Hardening** (Streamlit multipage UI, Red-team harness, 53 tests)

---

## 5. Verification & Acceptance Metrics

| Metric | Target | Actual Verified Result | Status |
|---|---|---|---|
| **PII Leakage across corpus** | 0 | **0 leaks** | PASSED ✅ |
| **Decision Replay Determinism** | 100% | **100% bitwise hash match** | PASSED ✅ |
| **Citation Validity** | $\ge 98\%$ | **100% (Non-cited claims abstain)** | PASSED ✅ |
| **Alert Volume Reduction** | 40–60% | **60% alert reduction (5 $\to$ 2 cases)** | PASSED ✅ |
| **Prompt-Injection Block Rate** | $\ge 95\%$ | **100% fail-safe neutralized** | PASSED ✅ |
| **T0 Decision Latency** | $< 300\text{ ms}$ | **$< 50\text{ ms}$** | PASSED ✅ |
| **Test Suite Passing** | 100% | **53 / 53 unit tests passing** | PASSED ✅ |
