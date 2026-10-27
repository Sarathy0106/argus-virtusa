"use client";

import { useRef, useState } from "react";
import { useCaseStore } from "@/store/case";
import { Panel } from "@/components/shell/Panel";

// Inbox (step 1): drag-and-drop uploader + 4 presets. On submit, a case starts
// and the clause/airlock events stream from the live SSE feed.
export default function InboxPage() {
  const { caseId, setCase, events } = useCaseStore();
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function start(body: FormData) {
    setBusy(true);
    try {
      const res = await fetch("/api/v2/cases", { method: "POST", body });
      const data = (await res.json()) as { case_id: string };
      setCase(data.case_id);
    } finally {
      setBusy(false);
    }
  }

  const stageEvents = events.filter((e) => e.type.startsWith("stage."));

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-heading text-2xl font-bold text-text">Circular Inbox</h1>

      <Panel state="live" title="Upload or pick a preset">
        <div className="flex flex-col gap-4">
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const f = e.dataTransfer.files?.[0];
              if (f) {
                const fd = new FormData();
                fd.set("file", f);
                void start(fd);
              }
            }}
            className="flex h-32 items-center justify-center rounded-card border border-dashed border-border text-sm text-muted"
          >
            Drag a PDF / MD / TXT circular here, or
            <button
              onClick={() => fileRef.current?.click()}
              className="ml-2 text-primary underline"
            >
              browse
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.md,.txt"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) {
                  const fd = new FormData();
                  fd.set("file", f);
                  void start(fd);
                }
              }}
            />
          </div>
          <div className="flex gap-2">
            {["C1", "C2", "C3", "C4"].map((p) => (
              <button
                key={p}
                disabled={busy}
                onClick={() => {
                  const fd = new FormData();
                  fd.set("preset_id", p);
                  void start(fd);
                }}
                className="rounded-btn border border-accent bg-elevated px-3 py-2 text-sm text-accent hover:bg-accent hover:text-bg disabled:opacity-50"
              >
                Preset {p}
              </button>
            ))}
          </div>
        </div>
      </Panel>

      <Panel
        state={caseId ? "live" : "empty"}
        title="Pipeline events (live)"
        emptyLabel="Start a case to see clauses and stages stream in."
      >
        <ul className="space-y-1 font-mono text-xs">
          {stageEvents.map((e) => (
            <li key={e.seq} className="flex gap-3">
              <span className="tabular text-muted">seq {e.seq}</span>
              <span className="text-primary">{e.type}</span>
              <span className="text-text">
                {String((e.payload.stage_name as string) ?? "")}
              </span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
