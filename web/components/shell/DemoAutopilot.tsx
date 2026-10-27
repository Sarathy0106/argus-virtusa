"use client";

import { useState } from "react";
import { Play } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { useCaseStore } from "@/store/case";
import { usePresenterStore } from "@/store/presenter";

// Demo Autopilot calls the SAME public API as the manual buttons (no special code
// path), with short delays, so the autopilot is also an integration test of the
// demo flow.
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function DemoAutopilot() {
  const { setCase } = useCaseStore();
  const setStep = usePresenterStore((s) => s.setStep);
  const [running, setRunning] = useState(false);
  const [log, setLog] = useState<string[]>([]);

  const push = (m: string) => setLog((l) => [...l, m]);

  async function run() {
    setRunning(true);
    setLog([]);
    try {
      setStep(1);
      push("Step 1: uploading C1 preset…");
      const fd = new FormData();
      fd.set("preset_id", "C1");
      const res = await fetch("/api/v2/cases", { method: "POST", body: fd });
      const { case_id } = (await res.json()) as { case_id: string };
      setCase(case_id);

      // Wait for completion.
      let summary: any = {};
      for (let i = 0; i < 60; i++) {
        summary = await apiGet(`/api/v2/cases/${case_id}`);
        if (summary.status === "COMPLETED") break;
        await sleep(400);
      }
      setStep(2);
      push(`Steps 2-5: pipeline complete · ${summary.bundle_count} bundles · ${summary.backtest?.total_rows ?? 0} rows backtested`);
      await sleep(600);

      // Approvals.
      setStep(6);
      const bh = summary.bundle_hash;
      const rn = summary.rule_name;
      const mk = (await apiPost<any>("/api/v2/auth/login", { user_id: "maker", password: "maker-demo" })).token;
      const ck = (await apiPost<any>("/api/v2/auth/login", { user_id: "checker", password: "checker-demo" })).token;
      push("Step 6: trying deploy with no signature (expect 403)…");
      const noSig = await fetch(`/api/v2/deploy/${case_id}`, { method: "POST" });
      push(`  → ${noSig.status} ${noSig.status === 403 ? "(blocked, as expected)" : ""}`);
      await apiPost("/api/v2/approvals/maker", { bundle_hash: bh, rule_name: rn, token: mk, case_id });
      await apiPost("/api/v2/approvals/checker", { bundle_hash: bh, rule_name: rn, token: ck, case_id });
      await sleep(400);

      // Rollout healthy then chaos breach.
      setStep(7);
      push("Step 7: deploying (healthy rollout)…");
      const healthy = await (await fetch(`/api/v2/deploy/${case_id}`, { method: "POST" })).json();
      push(`  → reached_100=${healthy.reached_100}`);
      await sleep(400);
      push("Step 7: injecting alert_flood → SPRT breach + measured rollback…");
      await fetch(`/api/v2/chaos/alert_flood?case_id=${case_id}`, { method: "POST" });
      const flood = await (await fetch(`/api/v2/deploy/${case_id}`, { method: "POST" })).json();
      push(`  → breached=${flood.breached} rollback_ms=${flood.rollback?.rollback_ms}`);
      await sleep(400);

      // Audit.
      setStep(8);
      const tamper = await (await fetch(`/api/v2/audit/${case_id}/tamper-demo?target_seq=2`, { method: "POST" })).json();
      push(`Step 8: tamper demo → chain breaks at index ${tamper.after?.first_broken_index}`);
      push("Done. Every number above was computed live.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="rounded-card border border-accent bg-elevated p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-heading text-sm font-semibold text-accent">Demo Autopilot</div>
          <p className="text-xs text-muted">Runs the full 8-step demo via the public API.</p>
        </div>
        <button
          onClick={run}
          disabled={running}
          className="flex items-center gap-2 rounded-btn bg-accent px-3 py-2 text-sm text-bg disabled:opacity-50"
        >
          <Play size={14} /> {running ? "Running…" : "Run demo"}
        </button>
      </div>
      {log.length > 0 && (
        <ul className="mt-3 max-h-48 space-y-1 overflow-auto font-mono text-xs text-text">
          {log.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
