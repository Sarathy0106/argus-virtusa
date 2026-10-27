"use client";

import { usePresenterStore } from "@/store/presenter";

// Talking points per demo step (Part 9). Shown only in Presenter Mode.
const STEPS: Record<number, { title: string; point: string }> = {
  1: { title: "Step 1 of 8: Intake", point: "Drag a circular in — clauses stream, PII airlocked." },
  2: { title: "Step 2 of 8: Obligations", point: "Applicable vs not, with the reason. C2 is not applicable." },
  3: { title: "Step 3 of 8: Rule Studio", point: "Z3 counter-example banner — the exact transaction." },
  4: { title: "Step 4 of 8: Objection loop", point: "Validator rejects; amber loop; iteration 2 passes." },
  5: { title: "Step 5 of 8: Impact", point: "500,000 rows processed; the real before/after delta." },
  6: { title: "Step 6 of 8: Approvals", point: "Deploy with one signature: real 403. Then both sign." },
  7: { title: "Step 7 of 8: Rollout", point: "Shadow overlay, canary ladder, SPRT chart." },
  8: { title: "Step 8 of 8: Audit", point: "Replay matches; tamper turns the chain red at the first broken index." },
};

export function PresenterHud() {
  const { on, step, setStep } = usePresenterStore();
  if (!on) return null;
  const info = STEPS[step] ?? STEPS[1];
  return (
    <div className="fixed bottom-4 left-1/2 z-40 w-[min(640px,90vw)] -translate-x-1/2 rounded-card border border-accent bg-elevated p-4 shadow-lg">
      <div className="flex items-center justify-between">
        <span className="font-heading text-sm font-semibold text-accent">{info.title}</span>
        <div className="flex gap-1">
          {Object.keys(STEPS).map((k) => {
            const n = Number(k);
            return (
              <button
                key={k}
                onClick={() => setStep(n)}
                className={`h-6 w-6 rounded-chip text-xs tabular ${
                  n === step ? "bg-accent text-bg" : "bg-surface text-muted"
                }`}
              >
                {n}
              </button>
            );
          })}
        </div>
      </div>
      <p className="mt-2 text-sm text-text">{info.point}</p>
    </div>
  );
}
