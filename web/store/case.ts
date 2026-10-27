import { create } from "zustand";
import type { ArgusEvent } from "@/lib/sse";

// Holds the currently-selected case and its live event stream. Events are the
// source of the UI's live state; nothing is synthesized client-side.
type CaseState = {
  caseId: string | null;
  events: ArgusEvent[];
  lastSeq: number;
  setCase: (id: string) => void;
  pushEvent: (ev: ArgusEvent) => void;
  reset: () => void;
};

export const useCaseStore = create<CaseState>((set) => ({
  caseId: null,
  events: [],
  lastSeq: 0,
  setCase: (id) => set({ caseId: id, events: [], lastSeq: 0 }),
  pushEvent: (ev) =>
    set((s) => ({
      events: [...s.events, ev],
      lastSeq: Math.max(s.lastSeq, ev.seq),
    })),
  reset: () => set({ caseId: null, events: [], lastSeq: 0 }),
}));
