"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

// Collapsible "view source" — keeps raw code/JSON available (TRUTH RULE) but out
// of the way so the main view can tell the human story.
export function ViewSource({
  label,
  code,
}: {
  label: string;
  code: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-btn border border-border bg-elevated">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-muted hover:text-text focus:outline-none focus:ring-2 focus:ring-primary"
        aria-expanded={open}
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {label}
      </button>
      {open && (
        <pre className="max-h-64 overflow-auto border-t border-border p-3 font-mono text-[11px] text-text">
          {code}
        </pre>
      )}
    </div>
  );
}
