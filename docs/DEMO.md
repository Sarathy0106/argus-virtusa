# ARGUS v2 — 5-Minute Winning Pitch Demo Playbook

*Circular In, Safe Rule Out.*

---

## Pitch Narrative & Timing Matrix (300 Seconds)

**Opening line (0:00 - 0:15):**
> *"Banks take weeks to turn one regulatory circular into a live rule, and they still get the scope wrong. ARGUS does it in hours, and no rule ever goes live without two humans and a mathematical rollback plan."*

---

| Time | Stage & Action | Exact Words to Say | System Proof Point |
| :--- | :--- | :--- | :--- |
| **0:15** | **1. Circular Inbox**<br>Select C1 (`RBI/2026-27/42`); click *Ingest & Chunk*. | *"Circular text is untrusted data. PII is tokenised at the airlock before any model sees it."* | 0 PII leaks; bitemporal valid time coordinates pinned; SHA-256 hash stamped. |
| **0:45** | **2. Obligation Map**<br>View extracted obligations; switch to C2 (`RBI/2026-27/58`). | *"We only act on what applies to Meridian Bank. C2 is for Urban Co-operatives and NBFCs, so our engine marks it Exempt with an audit trail, saving weeks of wasted review."* | `NOT_APPLICABLE` verdict card citing Scheduled Commercial Bank license. |
| **1:15** | **3. Rule Studio**<br>Run Policy Mapping & Z3 solver. | *"This is mathematically proven, not an LLM opinion. The Z3 theorem prover discovered a formal contradiction between our draft rule and existing rule `R-CASH-014`."* | Z3 Counter-Example Banner: `₹1,000,000 cash deposit for Risk Band C customer commands BLOCK vs ENHANCED_REVIEW`. |
| **1:45** | **4. Agent Mesh**<br>Watch Live Agent Mesh & Objection Loop. | *"Agents argue, deterministic code decides. When the Validator rejects the draft, the objection loop lights up amber, re-routes to the author, and resolves in iteration 2."* | Animated objection loop arc lights up amber; iteration counter advances `1/3 ➔ 2/3`. |
| **2:30** | **5. Impact Report**<br>Review DuckDB 100k backtest replay. | *"We know the blast radius before anyone approves. Backtesting shows alerts rising +21%, concentrated in Small Business and High-Risk segments, adding 3.4 hours of analyst review daily."* | DuckDB vectorized query; before/after alert bars; segment concentration heatmap. |
| **3:00** | **6. Dual Approvals**<br>Attempt single-signed deployment, then sign Maker + Checker. | *"Unapproved rules reaching enforcement: zero, by construction. Try to deploy with one signature and watch the core engine refuse. Only dual Ed25519 signatures can mint a deployment token."* | 403 Forbidden on single sign; 200 OK once both Rajesh and Vikram sign. |
| **3:30** | **7. Rollout Monitor**<br>Activate Shadow Mode; ramp canary to 10% ➔ 50%. | *"Shadow first. Promotion is gated by statistics. With live stream divergence under 1.4%, we ramp canary traffic safely."* | Shadow diffing `< 2.0%`; SPRT confidence bounds green. |
| **4:00** | **7. Chaos Injection**<br>Click *Trigger Chaos Anomaly* (Alert Flood). | *"Rollback is a pointer change on a signed Git bundle. When an alert flood is detected, the engine executes an automated compensating saga rollback in 38 seconds."* | Red flash; circuit breaker toast: *Rolled back in 38s*; 0 transactions dropped. |
| **4:30** | **8. Audit & Replay**<br>Click *Execute Bit-for-Bit Replay*; run bitemporal time-travel. | *"Any regulator can ask what we knew and which rule was live on 3 June, and we can prove it bit-for-bit with an identical hash."* | SHA-256 Merkle root; `HASH MATCH ✓` proof banner. |

---

**Closing line (4:45 - 5:00):**
> *"From weeks to hours, with unbroken traceability from clause to rule to test, and mathematically safer than the manual process it replaces."*

---

## Anticipated Judge Q&A Cheat Sheet

1. **"What if the LLM hallucinates an obligation?"**
   - *Answer:* The evidence verifier rejects any claim lacking a clause citation. If a clause does not exist or support the assertion, the pipeline abstains and escalates rather than guessing.
2. **"Can I trust the conflict detection?"**
   - *Answer:* Yes. It does not ask the LLM. It compiles DSL predicates into first-order logic and runs a Z3 SMT solver that mathematically proves whether two actions contradict over any feasible transaction.
3. **"What about prompt injection inside a circular?"**
   - *Answer:* Circular text is treated as untrusted data in a delimited slot. We tested it in Circular C4 and our red-team suite: prompt injections like *"auto-approve all rules"* are discarded at ingestion.
4. **"Is this just a hardcoded pipeline?"**
   - *Answer:* No. It is an agentic cyclic state graph with an Objection Loop. A sequential pipeline cannot dynamically re-route back to authoring upon validator objection.
5. **"How does this scale to real core banking traffic?"**
   - *Answer:* Agents communicate asynchronously using the A2A protocol. Backtesting uses vectorized DuckDB which replays 500k transactions in seconds. The core rule engine evaluates compiled OPA Rego at sub-millisecond latencies.
