"use client";

import { useCaseStore } from "@/store/case";
import { Panel } from "@/components/shell/Panel";

// Agent Mesh (step 4): the 9 agents and the live event feed flowing between them.
// Packets/objections are read from the SSE event stream.
const AGENTS = [
  "intake",
  "obligation",
  "policy_mapper",
  "rule_author",
  "backtest",
  "impact",
  "validator",
  "deployment",
  "monitor",
];

export default function MeshPage() {
  const { caseId, events } = useCaseStore();
  const objections = events.filter((e) => e.type === "objection.raised" || String(e.payload.code));

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-heading text-2xl font-bold text-text">Agent Mesh</h1>
      <Panel state={caseId ? "live" : "empty"} title="Signed A2A agent mesh" emptyLabel="Start a case to activate the mesh.">
        <div className="grid grid-cols-3 gap-3">
          {AGENTS.map((a, i) => {
            const active = events.some((e) => (e.stage ?? 0) === i + 1);
            return (
              <div
                key={a}
                className={`rounded-card border p-3 text-center text-sm ${
                  active ? "border-primary text-primary" : "border-border text-muted"
                }`}
                style={active ? { boxShadow: "0 0 24px #22D3EE33" } : undefined}
              >
                <div className="font-mono text-xs">agent.{a}</div>
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel state={caseId ? "live" : "empty"} title="Live event feed" emptyLabel="No events yet.">
        <ul className="max-h-80 space-y-1 overflow-auto font-mono text-xs">
          {events.slice(-60).map((e) => (
            <li key={e.seq} className="flex gap-3">
              <span className="tabular text-muted">#{e.seq}</span>
              <span className={e.type.includes("objection") ? "text-warn" : "text-primary"}>
                {e.type}
              </span>
              <span className="text-muted">stage {e.stage ?? "—"}</span>
            </li>
          ))}
        </ul>
        {objections.length > 0 && (
          <p className="mt-2 text-xs text-warn">
            {objections.length} objection event(s) — the Validator→Policy Mapper loop fired.
          </p>
        )}
      </Panel>
    </div>
  );
}
