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
