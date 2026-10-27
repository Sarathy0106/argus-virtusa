"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchMeta } from "@/lib/meta";
import type { Meta } from "@/lib/schemas";
import { Panel, type PanelState } from "@/components/shell/Panel";
import { TruthBadge } from "@/components/shell/TruthBadge";

// Mission Control (home). For R0 this renders the live /meta payload so the gate
// "home page renders from /meta" is satisfied with real backend data. Later
// phases (R3/R4) expand this into the full shell + KPI strip + case list.

export default function MissionControl() {
  const [state, setState] = useState<PanelState>("loading");
  const [meta, setMeta] = useState<Meta | null>(null);

  const load = useCallback(async () => {
    setState("loading");
    try {
      const m = await fetchMeta();
      setMeta(m);
      setState("live");
    } catch {
      setState("error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="mx-auto flex min-h-screen max-w-[1440px] flex-col gap-6 px-6 py-10">
      <header className="flex items-baseline justify-between">
        <div>
          <h1 className="font-heading text-[32px] font-bold text-text">
            ARGUS <span className="text-primary">Mission Control</span>
          </h1>
          <p className="mt-1 text-sm text-muted">
            Regulatory Circular → Live Rule. Every number is computed live.
          </p>
        </div>
        <span className="rounded-chip border border-border px-3 py-1 font-mono text-xs text-muted">
          v2 rebuild
        </span>
      </header>

      <Panel
        state={state}
        title="System status"
        onRetry={() => void load()}
        errorLabel="Could not reach the gateway /api/v2/meta. Is the API running on :8000?"
      >
        {meta && (
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label="Service" value={meta.service} mono />
            <Stat label="Version" value={meta.version} mono />
            <Stat label="LLM mode" value={meta.llm_mode} mono />
            <Stat
              label="Chain"
              value={meta.chain_verified ? "verified" : "broken"}
              tone={meta.chain_verified ? "ok" : "danger"}
            />
            <Stat
              label="Last event seq"
              value={String(meta.last_event_seq)}
              mono
            />
            <Stat label="Server time" value={meta.server_time} mono />
          </dl>
        )}
      </Panel>

      <div className="mt-auto">{meta && <TruthBadge meta={meta} />}</div>
    </main>
  );
}

function Stat({
  label,
  value,
  mono,
  tone,
}: {
  label: string;
  value: string;
  mono?: boolean;
  tone?: "ok" | "danger";
}) {
  const toneClass =
    tone === "ok" ? "text-ok" : tone === "danger" ? "text-danger" : "text-text";
  return (
    <div className="rounded-btn border border-border bg-elevated p-4">
      <dt className="text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd
        className={`mt-1 ${mono ? "font-mono" : "font-body"} tabular text-sm ${toneClass}`}
      >
        {value}
      </dd>
    </div>
  );
}
