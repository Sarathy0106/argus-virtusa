"use client";

import { useState } from "react";
import { useCaseStore } from "@/store/case";
import { Panel } from "@/components/shell/Panel";
import { MetricCard } from "@/components/ui/MetricCard";
import { fmtMs } from "@/lib/format";

// Rollout (step 7): canary ladder + SPRT from live events, chaos panel, and the
// measured rollback banner on breach.
export default function RolloutPage() {
  const { caseId, events } = useCaseStore();
  const [chaosMsg, setChaosMsg] = useState("");

  const canary = events.filter((e) => e.type === "canary.step");
  const sprt = events.filter((e) => e.type === "sprt.update");
  const breach = events.find((e) => e.type === "breach.detected");
  const rollback = events.find((e) => e.type === "rollback.completed");

  async function injectChaos(kind: string) {
    if (!caseId) return;
    await fetch(`/api/v2/chaos/${kind}?case_id=${caseId}`, { method: "POST" });
    setChaosMsg(`Injected ${kind} — redeploy to see the breach.`);
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-heading text-2xl font-bold text-text">Rollout &amp; Monitoring</h1>

      <Panel state={caseId ? "live" : "empty"} title="Canary ladder" emptyLabel="Deploy from Approvals to start the rollout.">
        <div className="flex gap-2">
          {["CANARY_1", "CANARY_10", "CANARY_50", "PROMOTED_100"].map((stage) => {
            const step = canary.find((e) => e.payload.stage === stage);
            const reached = Boolean(step);
            return (
              <div
                key={stage}
                className={`flex-1 rounded-btn border p-3 text-center text-xs ${
                  reached ? "border-ok text-ok" : "border-border text-muted"
                }`}
              >
                <div className="font-mono">{stage}</div>
                {step && (
                  <div className="mt-1 tabular text-text">
                    alert {String((step.payload.alert_rate_pct as number) ?? "—")}%
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel state={sprt.length ? "live" : caseId ? "loading" : "empty"} title="Wald SPRT" emptyLabel="No SPRT updates yet.">
        <ul className="space-y-1 font-mono text-xs">
          {sprt.map((e) => (
            <li key={e.seq} className="flex gap-3">
              <span className="text-muted">{String(e.payload.stage)}</span>
              <span className="tabular text-text">llr {String(e.payload.llr)}</span>
              <span className={String(e.payload.decision) === "ACCEPT_H1" ? "text-danger" : "text-ok"}>
                {String(e.payload.decision)}
              </span>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel state="live" title="Chaos panel">
        <div className="flex gap-2">
          {["alert_flood", "latency_spike", "drift"].map((k) => (
            <button
              key={k}
              disabled={!caseId}
              onClick={() => injectChaos(k)}
              className="rounded-btn border border-warn px-3 py-2 text-sm text-warn hover:bg-warn hover:text-bg disabled:opacity-40"
            >
              {k}
            </button>
          ))}
        </div>
        {chaosMsg && <p className="mt-2 text-xs text-muted">{chaosMsg}</p>}
      </Panel>

      {breach && (
        <div className="rounded-card border border-danger bg-elevated p-4" style={{ boxShadow: "0 0 24px #EF444433" }}>
          <div className="text-sm font-semibold text-danger">Breach detected — rolled back</div>
          <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
            <MetricCard
              label="Rollback (measured)"
              value={fmtMs(rollback?.payload.rollback_ms as number)}
              tone="danger"
              raw={rollback?.payload}
            />
            <MetricCard
              label="Breach stage"
              value={String(breach.payload.stage ?? "—")}
              tone="danger"
              raw={breach.payload}
            />
          </div>
        </div>
      )}
    </div>
  );
}
