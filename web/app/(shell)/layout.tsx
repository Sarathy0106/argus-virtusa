"use client";

import { useEffect, type ReactNode } from "react";
import { Sidebar } from "@/components/shell/Sidebar";
import { TopBar } from "@/components/shell/TopBar";
import { EvidenceDrawer } from "@/components/shell/EvidenceDrawer";
import { PresenterHud } from "@/components/shell/PresenterHud";
import { useCaseStore } from "@/store/case";
import { subscribeCaseEvents } from "@/lib/sse";

export default function ShellLayout({ children }: { children: ReactNode }) {
  const { caseId, pushEvent } = useCaseStore();

  // Subscribe to the active case's SSE stream once a case is selected, so the
  // stepper and live panels across pages stay in sync with real events.
  useEffect(() => {
    if (!caseId) return;
    const unsub = subscribeCaseEvents(caseId, pushEvent);
    return unsub;
  }, [caseId, pushEvent]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
      <EvidenceDrawer />
      <PresenterHud />
    </div>
  );
}
