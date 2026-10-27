import { create } from "zustand";

// Presenter HUD: enlarges fonts, hides debug, shows the current demo step + talking point.
type PresenterState = {
  on: boolean;
  step: number;
  toggle: () => void;
  setStep: (n: number) => void;
};

export const usePresenterStore = create<PresenterState>((set) => ({
  on: false,
  step: 1,
  toggle: () => set((s) => ({ on: !s.on })),
  setStep: (n) => set({ step: n }),
}));
