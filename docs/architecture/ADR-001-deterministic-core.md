# ADR-001: Deterministic Core with Probabilistic Edge

**Status:** ACCEPTED  
**Date:** 2026-10-26  
**Deciders:** ARGUS Architecture & Safety Team  
**Scope:** Core Decision Engine & LLM Integration Boundaries  

---

## 1. Context and Problem Statement

Financial crime compliance and fraud monitoring systems operate under strict regulatory scrutiny (RBI, FinCEN, FATF). In these domains:
1. **Regulated decisions must be deterministic and replayable.** If an auditor asks why a transaction was frozen or approved 6 months ago, the system must reproduce the identical verdict bit-for-bit using the archived inputs, rule versions, model weights, and seeds.
2. **LLMs are inherently non-deterministic and hallucination-prone.** Temperature 0 does not guarantee bitwise determinism across model revisions, hardware architectures, or floating-point variations.
3. **Customer PII must never leave the sovereign perimeter.** Regulators penalize institutions that send raw account numbers, PANs, Aadhaar numbers, or names to third-party or even unisolated LLM instances.

## 2. Decision

We establish the foundational architectural principle: **"Deterministic core, probabilistic edge."**

1. **Policy-as-Code Decides:** All authoritative verdicts (`ALLOW`, `HOLD`, `ESCALATE`, `BLOCK`) and risk tiers (`T0`, `T1`, `T2`, `T3`) are rendered strictly by Open Policy Agent (OPA) Rego bundles paired with calibrated Machine Learning models (LightGBM).
2. **LLMs Never Decide:** LLMs are confined strictly to peripheral edge tasks:
   - Parsing unstructured circulars into draft obligation schemas.
   - Drafting explanatory narratives for human analysts from verified evidence.
   - Generating draft policy rules for human compliance approval.
3. **Mandatory PII Airlock:** Every string entering an LLM or cross-agent boundary must be tokenized by the PII Airlock using format-preserving tokens (e.g. `<ACCT_7F3A>`). Egress filters actively terminate any response leaking raw identifiers.
4. **Canonical Hash-Chained Audit Ledger:** Every decision record archives:
   - `input_hash = SHA-256(canonical_json(inputs))`
   - `rule_bundle_ver`
   - `model_ver`
   - `output_hash = SHA-256(canonical_json(outputs))`
   Any drift in hash verification during replay triggers an immediate security alert.

## 3. Consequences

### Positive
- **100% Audit Replayability:** Complete compliance defense during regulatory examinations.
- **Zero Raw PII Exposure:** Safe usage of local or hosted models without privacy violations.
- **Elimination of Autonomous Hallucinated Decisions:** An LLM cannot freeze accounts or waive sanctions checks.

### Trade-offs & Mitigations
- **Explanation Overhead:** LLM explanations must be verified by an `EvidenceVerifier`. If the LLM generates claims without cited evidence IDs, the explanation is dropped in favor of a deterministic fallback template.
- **Latency Budget:** PII tokenization and detokenization introduce a 5–15ms overhead per case, which is absorbed inside the async investigation loop off the critical T0 path.
