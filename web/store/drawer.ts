import { create } from "zustand";
import type { ArgusEvent } from "@/lib/sse";

// Evidence drawer: clicking any metric/chip opens the source event(s) with their
// seq, entry_hash and raw JSON — the UI's answer to "is this real?".
type DrawerState = {
  open: boolean;
  title: string;
  events: ArgusEvent[];
  raw: unknown;
  show: (title: string, events: ArgusEvent[], raw?: unknown) => void;
  close: () => void;
};

export const useDrawerStore = create<DrawerState>((set) => ({
  open: false,
  title: "",
  events: [],
  raw: null,
  show: (title, events, raw = null) => set({ open: true, title, events, raw }),
  close: () => set({ open: false }),
}));
