"use client";

import { useCaseStore } from "@/store/case";
import { useCaseDetail } from "@/lib/hooks";
import { Panel } from "@/components/shell/Panel";
import { ViewSource } from "@/components/ui/ViewSource";

// Rule Studio (steps 3-4): tells the story in plain English — what the rule does,
// the exact transaction that proves the conflict, and the clause it traces to.
// The raw DSL / Rego / tests are one click away behind "view source".

const OP_WORDS: Record<string, string> = {
  GTE: "≥",
  LTE: "≤",
  EQ: "is",
  NEQ: "is not",
  IN: "is one of",
  NOT_IN: "is not one of",
};

const FIELD_WORDS: Record<string, string> = {
  amount: "amount",
  channel: "channel",
  is_cash: "cash deposit",
  risk_band: "risk band",
  mcc: "merchant category",
  segment: "segment",
  country: "country",
};

function conditionToWords(c: Record<string, unknown>): string {
  const field = String(c.field ?? "").replace(/^input\./, "");
  const label = FIELD_WORDS[field] ?? field;
  const op = OP_WORDS[String(c.operator)] ?? String(c.operator);
  let val = c.value;
  if (field === "amount" && typeof val === "number") {
    val = `₹${val.toLocaleString("en-IN")}`;
  }
  if (Array.isArray(val)) val = val.join(" / ");
  if (field === "is_cash") return "transaction is a cash deposit";
  return `${label} ${op} ${val}`;
}

export default function StudioPage() {
  const caseId = useCaseStore((s) => s.caseId);
  const detail = useCaseDetail(caseId);
  const bundles = ((detail.data?.bundles as unknown[]) ?? []) as Record<string, unknown>[];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-heading text-2xl font-bold text-text">Rule Studio</h1>
      <Panel
        state={!caseId ? "empty" : bundles.length ? "live" : "loading"}
        title="Drafted rules"
        emptyLabel="Start a case to author rules."
      >
        <div className="space-y-6">
          {bundles.map((b, i) => {
            const rule = (b.rule_definition ?? {}) as Record<string, unknown>;
            const action = (rule.action ?? {}) as Record<string, unknown>;
            const conditions = ((rule.conditions as unknown[]) ?? []) as Record<string, unknown>[];
            const citations = ((rule.citations as unknown[]) ?? []) as string[];
            const objections = ((b.objections as unknown[]) ?? []) as Record<string, unknown>[];
            const ce = objections.find((o) => o.counter_example)?.counter_example as
              | Record<string, unknown>
              | undefined;

            return (
              <div key={i} className="rounded-card border border-border bg-surface p-5">
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <div className="font-heading text-base font-semibold text-text">
                      {String(rule.rule_name ?? "rule").replace(/_/g, " ")}
                    </div>
                    <div className="font-mono text-xs text-muted">
                      v{String(rule.version ?? "")} · traces to {String(rule.clause_id ?? "—")}
                    </div>
                  </div>
                  <span className={`text-xs ${b.validation_passed ? "text-ok" : "text-warn"}`}>
                    {b.validation_passed ? "validated ✓" : "pending"} ·{" "}
                    {String(b.iterations)} iteration{Number(b.iterations) > 1 ? "s" : ""}
                  </span>
                </div>

                {/* Plain-English rule */}
                <div className="rounded-btn border border-border bg-elevated p-4">
                  <div className="text-xs uppercase tracking-wide text-muted">What this rule does</div>
                  <p className="mt-1 text-sm text-text">
                    When{" "}
                    {conditions.map((c, idx) => (
                      <span key={idx}>
                        {idx > 0 && <span className="text-muted"> and </span>}
                        <span className="text-primary">{conditionToWords(c)}</span>
                      </span>
                    ))}
                    , <span className="text-accent">{String(action.outcome ?? "HOLD")}</span>
                    {action.cooling_period_hours
                      ? ` with a ${action.cooling_period_hours}h cooling period`
                      : ""}
                    .
                  </p>
                  {citations.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {citations.map((c) => (
                        <span key={c} className="rounded-chip bg-surface px-2 py-0.5 font-mono text-[10px] text-muted">
                          {c}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Z3 counter-example as a human story + transaction card */}
                {ce && (
                  <div className="mt-3 rounded-btn border border-warn bg-elevated p-4">
                    <div className="text-xs font-semibold text-warn">
                      ⚠ Z3 proved an active conflict with a live rule
                    </div>
                    <p className="mt-1 text-sm text-text">
                      For this exact transaction, the new rule and the existing live rule disagree —
                      so the first draft was rejected and re-routed.
                    </p>
                    <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                      <TxnField label="Amount" value={ce.amount != null ? `₹${Number(ce.amount).toLocaleString("en-IN")}` : "—"} />
                      <TxnField label="Cash?" value={ce.is_cash ? "Yes" : "No"} />
                      <TxnField label="Risk band" value={String(ce.risk_band ?? "—")} />
                      <TxnField label="Channel" value={String(ce.channel ?? "—")} />
                    </div>
                    {ce.description != null && (
                      <p className="mt-2 font-mono text-[11px] text-muted">{String(ce.description)}</p>
                    )}
                  </div>
                )}

                {/* Raw code tucked away */}
                <div className="mt-3 space-y-2">
                  <ViewSource label="View compiled Rego" code={String(b.rego ?? "")} />
                  <ViewSource label="View generated tests" code={String(b.tests ?? "")} />
                  <ViewSource label="View rule DSL (JSON)" code={JSON.stringify(rule, null, 2)} />
                </div>
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}

function TxnField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-btn border border-border bg-surface p-2 text-center">
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-0.5 font-mono text-sm tabular text-text">{value}</div>
    </div>
  );
}
