"use client";

import type { ArgusEvent } from "@/lib/sse";
import { useDrawerStore } from "@/store/drawer";

// A metric tile that is clickable to open the evidence drawer with its source
// events / raw payload. Every number in the UI uses this so it's all auditable.
export function MetricCard({
  label,
  value,
  tone,
  evidenceTitle,
  events = [],
  raw,
}: {
  label: string;
  value: string;
  tone?: "ok" | "warn" | "danger" | "primary";
  evidenceTitle?: string;
  events?: ArgusEvent[];
  raw?: unknown;
}) {
  const show = useDrawerStore((s) => s.show);
  const toneClass =
    tone === "ok"
      ? "text-ok"
      : tone === "warn"
        ? "text-warn"
        : tone === "danger"
          ? "text-danger"
          : tone === "primary"
            ? "text-primary"
            : "text-text";
  const clickable = events.length > 0 || raw !== undefined;
  return (
    <button
      type="button"
      disabled={!clickable}
      onClick={() => clickable && show(evidenceTitle ?? label, events, raw)}
      className={`rounded-btn border border-border bg-elevated p-4 text-left transition-colors ${
        clickable ? "hover:border-primary focus:outline-none focus:ring-2 focus:ring-primary" : ""
      }`}
    >
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 tabular font-mono text-lg ${toneClass}`}>{value}</div>
      {clickable && <div className="mt-1 text-[10px] text-muted">click for evidence</div>}
    </button>
  );
}
