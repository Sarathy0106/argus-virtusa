"use client";

import { X } from "lucide-react";
import { useDrawerStore } from "@/store/drawer";

// Side drawer showing the source event(s) behind a clicked metric: seq,
// entry_hash and raw JSON. This is the "is this real?" proof surface.
export function EvidenceDrawer() {
  const { open, title, events, raw, close } = useDrawerStore();
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={close}
        aria-hidden
      />
      <aside className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-border bg-surface p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-heading text-lg font-semibold text-text">
            Evidence · {title}
          </h2>
          <button
            onClick={close}
            aria-label="Close evidence drawer"
            className="rounded-btn p-1 text-muted hover:text-text focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <X size={18} />
          </button>
        </div>
        <p className="mb-3 text-xs text-muted">
          Every value shown in the UI traces to a backend event below.
        </p>
        <div className="flex-1 space-y-3 overflow-auto">
          {events.length === 0 && raw == null && (
            <p className="text-sm text-muted">No source events captured.</p>
          )}
          {events.map((ev) => (
            <div
              key={ev.seq}
              className="rounded-btn border border-border bg-elevated p-3"
            >
              <div className="mb-1 flex items-center justify-between font-mono text-xs">
                <span className="text-primary">{ev.type}</span>
                <span className="tabular text-muted">seq {ev.seq}</span>
              </div>
              {ev.entry_hash && (
                <div className="mb-2 break-all font-mono text-[10px] text-muted">
                  {ev.entry_hash}
                </div>
              )}
              <pre className="overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] text-text">
                {JSON.stringify(ev.payload, null, 2)}
              </pre>
            </div>
          ))}
          {raw != null && (
            <div className="rounded-btn border border-border bg-elevated p-3">
              <div className="mb-1 font-mono text-xs text-primary">raw response</div>
              <pre className="overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] text-text">
                {JSON.stringify(raw, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
