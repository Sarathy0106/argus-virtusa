"use client";

import { useCaseStore } from "@/store/case";
import { Panel } from "@/components/shell/Panel";

// Agent Mesh (step 4): a visual pipeline of the 9 signed agents. Each node lights
// up as its stage runs; the Validator → Policy Mapper edge turns amber when an
// objection is raised. The story, not a raw log.

const AGENTS: { id: string; label: string; stage: number }[] = [
  { id: "intake", label: "Intake", stage: 1 },
  { id: "obligation", label: "Obligation", stage: 2 },
  { id: "policy_mapper", label: "Policy Mapper", stage: 3 },
  { id: "rule_author", label: "Rule Author", stage: 4 },
  { id: "backtest", label: "Backtest", stage: 5 },
  { id: "impact", label: "Impact", stage: 6 },
  { id: "validator", label: "Validator", stage: 7 },
  { id: "deployment", label: "Deployment", stage: 9 },
  { id: "monitor", label: "Monitor", stage: 10 },
];

const HUMAN: Record<string, string> = {
  "stage.started": "started working",
  "stage.completed": "finished",
  "backtest.progress": "scanning transactions",
  "objection.raised": "raised an objection",
  "canary.step": "advanced the canary",
  "sprt.update": "updated SPRT",
  "breach.detected": "detected a breach",
  "rollback.completed": "rolled back",
};

export default function MeshPage() {
  const { caseId, events } = useCaseStore();

  const reachedStage = events.reduce((max, e) => Math.max(max, e.stage ?? 0), 0);
  const objections = events.filter(
    (e) => e.type === "objection.raised" || String(e.payload.code).includes("CONFLICT"),
  );
  const hasObjection = objections.length > 0;

  // Build a compact, human-readable activity list (last 8 meaningful events).
  const activity = events
    .filter((e) => HUMAN[e.type])
    .slice(-8)
    .reverse();

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-heading text-2xl font-bold text-text">Agent Mesh</h1>

      <Panel
        state={caseId ? "live" : "empty"}
        title="Signed A2A mesh"
        emptyLabel="Start a case to activate the mesh."
      >
        <div className="relative flex flex-wrap items-stretch gap-x-2 gap-y-6">
          {AGENTS.map((a, i) => {
            const done = reachedStage > a.stage;
            const active = reachedStage === a.stage;
            const isValidator = a.id === "validator";
            const tone = isValidator && hasObjection && active
              ? "border-warn text-warn"
              : done
                ? "border-ok text-ok"
                : active
                  ? "border-primary text-primary"
                  : "border-border text-muted";
            return (
              <div key={a.id} className="flex items-center gap-2">
                <div
                  className={`flex h-20 w-28 flex-col items-center justify-center rounded-card border text-center ${tone}`}
                  style={active ? { boxShadow: "0 0 24px #22D3EE33" } : undefined}
                >
                  <span className="text-xs font-semibold">{a.label}</span>
                  <span className="mt-1 font-mono text-[10px] text-muted">agent.{a.id}</span>
                  <span className="mt-1 text-[10px]">
                    {done ? "done ✓" : active ? "running…" : "idle"}
                  </span>
                </div>
                {i < AGENTS.length - 1 && (
                  <span className={`text-lg ${done ? "text-ok" : "text-border"}`}>→</span>
                )}
              </div>
            );
          })}
        </div>

        {hasObjection && (
          <div className="mt-4 rounded-btn border border-warn bg-elevated p-3 text-sm text-warn">
            ↩ Objection loop: the Validator rejected the draft and routed it back to the Policy
            Mapper. The corrected rule passed on the next iteration.
          </div>
        )}
      </Panel>

      <Panel state={caseId ? "live" : "empty"} title="Recent agent activity" emptyLabel="No activity yet.">
        <ul className="space-y-2">
          {activity.map((e) => {
            const agent = AGENTS.find((a) => a.stage === e.stage);
            return (
              <li key={e.seq} className="flex items-center gap-3 text-sm">
                <span className={`h-2 w-2 rounded-full ${e.type.includes("objection") ? "bg-warn" : "bg-primary"}`} />
                <span className="text-text">{agent ? agent.label : `Stage ${e.stage ?? "—"}`}</span>
                <span className="text-muted">{HUMAN[e.type]}</span>
                <span className="ml-auto flex items-center gap-1 text-[10px] text-ok">
                  <span>🔒 signed</span>
                </span>
              </li>
            );
          })}
          {activity.length === 0 && caseId && (
            <li className="text-sm text-muted">Waiting for the pipeline to emit events…</li>
          )}
        </ul>
      </Panel>
    </div>
  );
}
