# 🛡️ ARGUS v2 — Circular to Live Rule Engine

> **Agentic Regulatory & Risk Guard with Unified Safety**  
> *"Deterministic core, probabilistic edge"* · **FDS NA Use Case 2 Re-aligned**

---

## 🎯 System Overview

ARGUS v2 pivots from generic case triage to an autonomous, 10-stage regulatory translation and deployment pipeline: **"Circular in, safe rule out"**. 

It autonomously ingests regulatory circulars (e.g., RBI, OCC, FINRA), evaluates their applicability against specific **Bank Profiles**, identifies **Gaps, Overlaps, and Conflicts** against internal policies, drafts human-readable **Rule DSL (YAML)**, compiles directly to **Open Policy Agent (OPA) Rego**, backtests in an isolated sandbox over **100,000 historical transactions**, subjects candidate rules to an **independent Validator Gate & Objection Loop**, enforces **Maker-Checker Dual Governance with Ed25519 Cryptographic Signatures**, executes non-enforcing **Shadow Evaluation**, and runs canary rollouts with **sub-second automated rollbacks (<500ms)** upon metric breach.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                ARGUS v2 10-STAGE REGULATORY PIPELINE                                  │
├───────────────┬──────────────────────────┬─────────────────────────┬───────────────────┬───────────────┤
│ Stage 1       │ Stage 2                  │ Stage 3                 │ Stage 4           │ Stage 5 & 6   │
│ Circular      │ Obligation Extraction    │ Policy Mapping          │ Rule Authoring    │ Backtest &    │
│ Intake        │ & Bank Applicability     │ (Gaps & Conflicts)      │ (YAML DSL & Rego) │ Impact Ops    │
├───────────────┼──────────────────────────┼─────────────────────────┼───────────────────┼───────────────┤
│ Stage 7       │ Stage 8                  │ Stage 9                 │ Stage 10          │ Audit         │
│ Validator     │ Governance Approvals     │ Shadow Mode             │ Canary Ramp &     │ SHA-256 Chain │
│ Objection Loop│ (Maker-Checker, Ed25519) │ Non-Enforcing           │ Auto-Rollback     │ Replay Proof  │
└───────────────┴──────────────────────────┴─────────────────────────┴───────────────────┴───────────────┘
```

---

## ⚡ Quick Start: Streamlit Console & FastAPI Gateway

### 1. Prerequisites
- Python 3.11+
- Virtualenv activated

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run FastAPI Gateway (Background Daemon)
```bash
python -m uvicorn services.gateway.main:app --port 8001
```

### 4. Run ARGUS Multi-Page Streamlit Console
```bash
python -m streamlit run ui/app.py --server.port 8501
```

Open **http://localhost:8501** in your browser.

---

## 🧭 Multi-Page Console Structure

| Page | URL Path | Regulatory Stage | Description |
|---|---|---|---|
| **Hub** | `ui/app.py` | Global Overview | Bank profile switcher, 10-stage visual stepper, live telemetry KPIs |
| **1. Circular Inbox** | `ui/pages/1_circular_inbox.py` | Stage 1 | Regulatory circular intake, Docling/Marker clause extraction, PII Airlock |
| **2. Obligation Map** | `ui/pages/2_obligation_map.py` | Stage 2 | Clause obligations mapped to Bank Profile (Apex SCB vs. FinZap Payments Bank) |
| **3. Policy Mapping** | `ui/pages/3_policy_mapping.py` | Stage 3 | Internal policy cross-reference: Gap detection and Conflict detection |
| **4. Rule Studio** | `ui/pages/4_rule_studio.py` | Stage 4 | YAML Rule DSL authoring, OPA Rego compilation, unit tests, draft-only lock |
| **5. Backtest & Impact** | `ui/pages/5_backtest_impact.py` | Stages 5 & 6 | Sandbox replay over 100k transactions, volume delta & ops capacity analysis |
| **6. Validator Loop** | `ui/pages/6_validator_objection_loop.py`| Stage 7 | Independent Validator Gate: catches retail conflict on Iter 1, approves on Iter 2 |
| **7. Governance** | `ui/pages/7_governance_approvals.py` | Stage 8 | Maker-Checker dual human signoff with Ed25519 cryptographic signatures |
| **8. Rollout & Monitor**| `ui/pages/8_rollout_monitor.py` | Stages 9 & 10 | Shadow traffic evaluation, canary ramp, interactive sub-second auto-rollback |
| **9. Audit Explorer** | `ui/pages/9_audit_explorer.py` | Verification | SHA-256 Merkle chain verification & bit-for-bit deterministic replay engine |

---

## ⏱️ Recommended 5-Minute Live Demo Script (Section 13)

1. **Minute 1 — Bank Profile Applicability (Stage 1 & 2)**:
   - Select RBI Wire Transfer Circular (`RBI/2026/04/MD-WIRE`) in **1. Circular Inbox**.
   - Navigate to **2. Obligation Map**. Switch Bank Profile to `BANK-FINZAP-02` (Payments Bank) to demonstrate how ARGUS autonomously suppresses rule generation (`NOT_APPLICABLE`) because Payments Banks lack AD-Cat 1 Forex licenses. Switch back to `BANK-APEX-01` (`APPLICABLE`).
2. **Minute 2 — Policy Mapping & Conflict Detection (Stage 3)**:
   - In **3. Policy Mapping**, show how Clause 4.2 maps to internal policies, revealing both a statutory coverage **Gap** against `POL-WIRE-INTL-01` and a **Conflict** against the retail daily transfer limit `POL-LIMITS-RETAIL-04` (₹500,000 ceiling).
3. **Minute 3 — YAML DSL, Rego & Backtest Sandbox (Stages 4, 5 & 6)**:
   - In **4. Rule Studio**, view the auto-generated YAML Rule DSL and compiled OPA Rego with 100% test pass rate.
   - In **5. Backtest & Impact**, inspect the sandbox replay over 100,000 transactions showing a 14.5 hr/mo ops load delta absorbable by existing surplus capacity.
4. **Minute 3.5 — Validation Gate & Objection Loop (Stage 7)**:
   - In **6. Validator & Objection Loop**, run Iteration 1 to demonstrate the Validator catching the unscoped retail conflict. Click **'Resolve Objection & Re-author Scoped Rule'** to see Iteration 2 inject `account_category: ['CORPORATE', 'AD_CAT1']` and achieve green approval.
5. **Minutes 4 to 5 — Dual Signoff, Canary & Sub-Second Rollback (Stages 8, 9 & 10)**:
   - In **7. Governance Approvals**, sign the candidate rule with dual Maker and Checker keys.
   - In **8. Rollout & Monitor**, witness the live 10% canary traffic stream with 0.00% shadow discrepancy. Click **'Simulate Metric Anomaly & Trigger Rollback'** to see the system autonomously revert from `v1.1.0-canary` back to `v1.0.0` in **480 milliseconds**.
   - Finally, in **9. Audit Explorer**, run **'Verify Entire Hash Chain Integrity'** to mathematically prove zero tampering across all 8 forward-chained SHA-256 blocks.

---

## 🧪 Automated Testing

Run the comprehensive pytest suite verifying all 10 stages:

```bash
# Run v2 regulatory pipeline tests
python -m pytest tests/test_v2_circular_engine.py -v

# Run entire repository test suite (all 64 unit tests)
python -m pytest tests/ -q
```
