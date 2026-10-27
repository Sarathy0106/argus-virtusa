"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { useCaseStore } from "@/store/case";
import { Panel } from "@/components/shell/Panel";
import { shortHash } from "@/lib/format";

type LedgerResp = {
  total_blocks: number;
  integrity_verified: boolean;
  merkle_root: string;
  blocks: { seq: number; block_hash: string; event_type: string }[];
};

// Audit (step 8): hash-chain strip, real Merkle root, inclusion proof, and the
// tamper demo that turns the chain red at the first broken index.
export default function AuditPage() {
  const caseId = useCaseStore((s) => s.caseId);
  const [ledger, setLedger] = useState<LedgerResp | null>(null);
  const [tamper, setTamper] = useState<Record<string, unknown> | null>(null);
  const [inclusion, setInclusion] = useState<Record<string, unknown> | null>(null);

  async function load() {
    if (!caseId) return;
    setLedger(await apiGet<LedgerResp>(`/api/v2/audit/${caseId}/ledger`));
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId]);

  async function runTamper(seq: number) {
    if (!caseId) return;
    setTamper(await apiPost(`/api/v2/audit/${caseId}/tamper-demo?target_seq=${seq}`));
  }
  async function proveInclusion(seq: number) {
    if (!caseId) return;
    setInclusion(await apiGet(`/api/v2/audit/${caseId}/inclusion/${seq}`));
  }

  const brokenIdx = (tamper?.after as Record<string, number> | undefined)?.first_broken_index;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-heading text-2xl font-bold text-text">Audit Ledger</h1>

      <Panel state={caseId ? (ledger ? "live" : "loading") : "empty"} title="Hash chain" emptyLabel="Start a case to view its ledger." onRetry={load}>
        {ledger && (
          <>
            <div className="mb-3 flex flex-wrap gap-4 text-xs">
              <span className="text-muted">blocks: <span className="tabular text-text">{ledger.total_blocks}</span></span>
              <span className={ledger.integrity_verified ? "text-ok" : "text-danger"}>
                chain {ledger.integrity_verified ? "verified ✓" : "broken ✗"}
              </span>
              <span className="font-mono text-muted">merkle: {shortHash(ledger.merkle_root)}</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {ledger.blocks.map((b) => {
                const broken = brokenIdx != null && b.seq >= brokenIdx;
                return (
                  <button
                    key={b.seq}
                    onClick={() => proveInclusion(b.seq)}
                    title={`${b.event_type} · ${b.block_hash}`}
                    className={`h-8 w-8 rounded-btn border text-[10px] tabular ${
                      broken ? "border-danger bg-danger/20 text-danger" : "border-border text-muted hover:border-primary"
                    }`}
                  >
                    {b.seq}
                  </button>
                );
              })}
            </div>
          </>
        )}
      </Panel>

      <Panel state={caseId ? "live" : "empty"} title="Tamper demo (on a copy)" emptyLabel="Start a case first.">
        <div className="flex items-center gap-3">
          <button onClick={() => runTamper(2)} className="rounded-btn border border-danger px-3 py-2 text-sm text-danger hover:bg-danger hover:text-bg">
            Flip a bit at seq 2
          </button>
          {tamper && (
            <span className="font-mono text-xs text-text">
              before: {String((tamper.before as Record<string, unknown>).verified)} → after:{" "}
              <span className="text-danger">{String((tamper.after as Record<string, unknown>).verified)}</span> · first broken index{" "}
              <span className="text-danger">{String(brokenIdx)}</span>
            </span>
          )}
        </div>
        <p className="mt-2 text-xs text-muted">The live ledger is never mutated — tampering runs on a copy.</p>
      </Panel>

      {inclusion && (
        <Panel state="live" title={`Merkle inclusion proof · seq ${String(inclusion.index)}`}>
          <div className="text-xs">
            verified:{" "}
            <span className={inclusion.verified ? "text-ok" : "text-danger"}>
              {String(inclusion.verified)}
            </span>
          </div>
          <pre className="mt-2 max-h-48 overflow-auto font-mono text-[11px] text-text">
            {JSON.stringify(inclusion, null, 2)}
          </pre>
        </Panel>
      )}
    </div>
  );
}
