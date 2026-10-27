"use client";

// The 10-stage pipeline stepper pinned to the top bar. `current` is derived from
// the live case state / SSE events.
const STAGES = [
  "Intake",
  "Obligations",
  "Mapping",
  "Authoring",
  "Backtest",
  "Impact",
  "Validation",
  "Approval",
  "Shadow",
  "Rollout",
];

export function StageStepper({ current }: { current: number }) {
  return (
    <ol className="flex items-center gap-1 overflow-x-auto" aria-label="Pipeline stages">
      {STAGES.map((label, i) => {
        const n = i + 1;
        const state = n < current ? "done" : n === current ? "active" : "todo";
        return (
          <li key={label} className="flex items-center gap-1">
            <div
              className={`flex items-center gap-1.5 rounded-chip px-2 py-1 text-[11px] ${
                state === "done"
                  ? "text-ok"
                  : state === "active"
                    ? "bg-elevated text-primary"
                    : "text-muted"
              }`}
              title={`Stage ${n}: ${label}`}
            >
              <span className="tabular font-mono">{n}</span>
              <span className="hidden lg:inline">{label}</span>
            </div>
            {n < STAGES.length && <span className="text-border">·</span>}
          </li>
        );
      })}
    </ol>
  );
}
