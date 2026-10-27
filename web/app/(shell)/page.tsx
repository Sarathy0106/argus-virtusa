"use client";

import { useRouter } from "next/navigation";
import { apiPost } from "@/lib/api";
import { useMeta, useCaseSummary } from "@/lib/hooks";
import { useCaseStore } from "@/store/case";
import { TruthBadge } from "@/components/shell/TruthBadge";
import { MetricCard } from "@/components/ui/MetricCard";
import { Panel } from "@/components/shell/Panel";
import { DemoAutopilot } from "@/components/shell/DemoAutopilot";
import { fmtInt } from "@/lib/format";

// Mission Control: start a demo case, show KPI strip + truth badge. All numbers
// come from /meta and the case summary.
export default function MissionControl() {
  const router = useRouter();
  const meta = useMeta();
  const { caseId, setCase } = useCaseStore();
  const summary = useCaseSummary(caseId);

  async function runPreset(preset: string) {
    const fd = new FormData();
    fd.set("preset_id", preset);
    const res = await fetch("/api/v2/cases", { method: "POST", body: fd });
    const data = (await res.json()) as { case_id: string };
    setCase(data.case_id);
  }

  const s = (summary.data ?? {}) as Record<string, unknown>;
  const bt = (s.backtest ?? null) as Record<string, number> | null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-text">Mission Control</h1>
          <p className="text-sm text-muted">Circular → live rule. Every number is computed live.</p>
        </div>
        <div className="flex gap-2">
          {["C1", "C2", "C3", "C4"].map((p) => (
            <button
              key={p}
              onClick={() => runPreset(p)}
              className="rounded-btn border border-accent bg-elevated px-3 py-2 text-sm text-accent hover:bg-accent hover:text-bg focus:outline-none focus:ring-2 focus:ring-primary"
            >
              Run {p}
            </button>
          ))}
          <button
            onClick={() => router.push("/inbox")}
            className="rounded-btn border border-border px-3 py-2 text-sm text-muted hover:text-text"
          >
            Upload…
          </button>
        </div>
      </div>

      <Panel state={caseId ? "live" : "empty"} title="Active case" emptyLabel="Run a preset (C1–C4) or upload a circular to start a case.">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <MetricCard label="Case" value={String(caseId ?? "—")} />
          <MetricCard label="Status" value={String(s.status ?? "…")} tone="primary" raw={s} />
          <MetricCard label="Bundles" value={fmtInt(s.bundle_count as number)} raw={s} />
          <MetricCard
            label="Rows backtested"
            value={fmtInt(bt?.total_rows)}
            raw={bt}
            tone="ok"
          />
        </div>
      </Panel>

      <Panel state={meta.data ? "live" : meta.isError ? "error" : "loading"} title="System status" onRetry={() => meta.refetch()}>
        {meta.data && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <MetricCard label="LLM mode" value={meta.data.llm_mode} raw={meta.data} />
            <MetricCard
              label="Chain"
              value={meta.data.chain_verified ? "verified" : "broken"}
              tone={meta.data.chain_verified ? "ok" : "danger"}
              raw={meta.data}
            />
            <MetricCard label="Last event seq" value={String(meta.data.last_event_seq)} raw={meta.data} />
            <MetricCard label="Version" value={meta.data.version} />
          </div>
        )}
      </Panel>

      <DemoAutopilot />

      {meta.data && <TruthBadge meta={meta.data} />}
    </div>
  );
}
