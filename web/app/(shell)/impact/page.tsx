"use client";

import { useCaseStore } from "@/store/case";
import { useCaseSummary } from "@/lib/hooks";
import { Panel } from "@/components/shell/Panel";
import { MetricCard } from "@/components/ui/MetricCard";
import { fmtInt } from "@/lib/format";

// Impact (step 5): real 500k backtest — rows processed, before/after bars, and
// a per-segment breakdown. All counts come from the DuckDB backtest.
export default function ImpactPage() {
  const { caseId, events } = useCaseStore();
  const summary = useCaseSummary(caseId);
  const bt = (summary.data?.backtest ?? null) as Record<string, unknown> | null;
  const progress = events.filter((e) => e.type === "backtest.progress");
  const lastProgress = progress[progress.length - 1]?.payload as
    | { processed: number; total: number }
    | undefined;

  const segments = ((bt?.segments as unknown[]) ?? []) as Record<string, number>[];
  const maxSeg = Math.max(1, ...segments.map((s) => s.candidate_alerts));

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-heading text-2xl font-bold text-text">Impact Analysis</h1>

      <Panel state={caseId ? "live" : "empty"} title="Backtest progress (500k rows)" emptyLabel="Start a case to run the backtest.">
        <div className="mb-3 h-3 w-full overflow-hidden rounded-chip bg-elevated">
          <div
            className="h-full bg-primary transition-all"
            style={{
              width: lastProgress
                ? `${(lastProgress.processed / lastProgress.total) * 100}%`
                : bt
                  ? "100%"
                  : "0%",
            }}
          />
        </div>
        <p className="font-mono text-xs text-muted">
          {lastProgress
            ? `${fmtInt(lastProgress.processed)} / ${fmtInt(lastProgress.total)} rows`
            : bt
              ? `${fmtInt(bt.total_rows as number)} rows processed`
              : "waiting…"}
        </p>
      </Panel>

      <Panel state={bt ? "live" : caseId ? "loading" : "empty"} title="Before / after" emptyLabel="No backtest yet.">
        {bt && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <MetricCard label="Baseline alerts" value={fmtInt(bt.baseline_alerts as number)} raw={bt} />
            <MetricCard label="Candidate alerts" value={fmtInt(bt.candidate_alerts as number)} tone="primary" raw={bt} />
            <MetricCard label="Delta" value={fmtInt(bt.delta_alerts as number)} tone="warn" raw={bt} />
            <MetricCard label="Ops hours/day" value={String(bt.ops_hours_per_day ?? "—")} raw={bt} />
          </div>
        )}
      </Panel>

      <Panel state={segments.length ? "live" : caseId ? "loading" : "empty"} title="Per-segment candidate alerts" emptyLabel="No segment data yet.">
        <div className="space-y-2">
          {segments.map((s) => (
            <div key={s.segment as unknown as string} className="flex items-center gap-3">
              <span className="w-32 text-xs text-muted">{String(s.segment)}</span>
              <div className="h-4 flex-1 overflow-hidden rounded-chip bg-elevated">
                <div
                  className="h-full bg-accent"
                  style={{ width: `${(s.candidate_alerts / maxSeg) * 100}%` }}
                />
              </div>
              <span className="w-16 text-right font-mono text-xs tabular text-text">
                {fmtInt(s.candidate_alerts)}
              </span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
