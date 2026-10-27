"use client";

import { useCaseStore } from "@/store/case";
import { useCaseDetail } from "@/lib/hooks";
import { Panel } from "@/components/shell/Panel";

// Rule Studio (steps 3-4): per bundle, show the DSL/Rego, generated tests, and
// the Z3 counter-example banner when the objection loop fired.
export default function StudioPage() {
  const caseId = useCaseStore((s) => s.caseId);
  const detail = useCaseDetail(caseId);
  const bundles = ((detail.data?.bundles as unknown[]) ?? []) as Record<string, unknown>[];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-heading text-2xl font-bold text-text">Rule Studio</h1>
      <Panel
        state={!caseId ? "empty" : bundles.length ? "live" : "loading"}
        title="Rule bundles"
        emptyLabel="Start a case to author rules."
      >
        <div className="space-y-6">
          {bundles.map((b, i) => {
            const rule = (b.rule_definition ?? {}) as Record<string, unknown>;
            const objections = ((b.objections as unknown[]) ?? []) as Record<string, unknown>[];
            const ce = objections.find((o) => o.counter_example)?.counter_example as
              | Record<string, unknown>
              | undefined;
            return (
              <div key={i} className="rounded-card border border-border bg-surface p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-mono text-sm text-text">
                    {String(rule.rule_name ?? "bundle")} v{String(rule.version ?? "")}
                  </span>
                  <span
                    className={`text-xs ${b.validation_passed ? "text-ok" : "text-warn"}`}
                  >
                    {b.validation_passed ? "validated ✓" : "pending"} · {String(b.iterations)} iter
                  </span>
                </div>

                {ce && (
                  <div className="mb-3 rounded-btn border border-warn bg-elevated p-3">
                    <div className="text-xs font-semibold text-warn">
                      Z3 counter-example (active conflict)
                    </div>
                    <pre className="mt-1 overflow-auto font-mono text-[11px] text-text">
                      {JSON.stringify(ce, null, 2)}
                    </pre>
                  </div>
                )}

                <div className="grid gap-3 lg:grid-cols-2">
                  <CodeBlock title="Rule DSL" code={JSON.stringify(rule.conditions ?? [], null, 2)} />
                  <CodeBlock title="Compiled Rego" code={String(b.rego ?? "")} />
                </div>
                <CodeBlock title="Generated tests (Rego)" code={String(b.tests ?? "")} />
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}

function CodeBlock({ title, code }: { title: string; code: string }) {
  return (
    <div className="rounded-btn border border-border bg-elevated">
      <div className="border-b border-border px-3 py-1.5 text-xs text-muted">{title}</div>
      <pre className="max-h-64 overflow-auto p-3 font-mono text-[11px] text-text">{code}</pre>
    </div>
  );
}
