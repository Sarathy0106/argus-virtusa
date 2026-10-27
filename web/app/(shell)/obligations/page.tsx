"use client";

import { useCaseStore } from "@/store/case";
import { useCaseDetail } from "@/lib/hooks";
import { Panel } from "@/components/shell/Panel";

// Obligations (step 2): applicability verdict per obligation with the reason.
export default function ObligationsPage() {
  const caseId = useCaseStore((s) => s.caseId);
  const detail = useCaseDetail(caseId);
  const obligations = ((detail.data?.obligations as unknown[]) ?? []) as Record<string, unknown>[];

  const verdictTone = (v: string) =>
    v === "APPLICABLE" ? "text-ok" : v === "NOT_APPLICABLE" ? "text-muted" : "text-warn";

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-heading text-2xl font-bold text-text">Obligations</h1>
      <Panel
        state={!caseId ? "empty" : detail.isError ? "error" : obligations.length ? "live" : "loading"}
        title="Extracted obligations + applicability"
        emptyLabel="Start a case to extract obligations."
        onRetry={() => detail.refetch()}
      >
        <div className="grid gap-3 md:grid-cols-2">
          {obligations.map((o) => (
            <div key={String(o.id)} className="rounded-card border border-border bg-elevated p-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-muted">{String(o.clause_id)}</span>
                <span className={`text-xs font-semibold ${verdictTone(String(o.applicability))}`}>
                  {String(o.applicability).replace("_", " ")}
                </span>
              </div>
              <div className="mt-2 text-sm text-text">{String(o.actor)}</div>
              <div className="mt-1 text-xs text-muted">rule: {String(o.rule_ref)}</div>
              <p className="mt-2 text-xs text-muted">{String(o.rationale)}</p>
            </div>
          ))}
          {obligations.length === 0 && caseId && (
            <p className="text-sm text-muted">
              No applicable obligations (e.g. C2 is not applicable, C4 injection ignored).
            </p>
          )}
        </div>
      </Panel>
    </div>
  );
}
