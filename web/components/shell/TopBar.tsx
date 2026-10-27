"use client";

import { Presentation } from "lucide-react";
import { StageStepper } from "@/components/pipeline/StageStepper";
import { usePresenterStore } from "@/store/presenter";
import { useCaseStore } from "@/store/case";

// Top bar with the pinned 10-stage stepper. `current` is derived from the last
// stage event on the active case.
export function TopBar() {
  const presenter = usePresenterStore();
  const events = useCaseStore((s) => s.events);
  const stageEvents = events.filter((e) => typeof e.stage === "number");
  const current =
    stageEvents.length > 0 ? (stageEvents[stageEvents.length - 1].stage as number) : 1;

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-surface px-6">
      <StageStepper current={current} />
      <button
        onClick={presenter.toggle}
        className={`flex items-center gap-2 rounded-btn border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
          presenter.on
            ? "border-accent bg-elevated text-accent"
            : "border-border text-muted hover:text-text"
        }`}
        aria-pressed={presenter.on}
      >
        <Presentation size={16} aria-hidden />
        Presenter
      </button>
    </header>
  );
}
