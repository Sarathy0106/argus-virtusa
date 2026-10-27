import type { Meta } from "@/lib/schemas";

// The truth badge reads ONLY from /meta and the ledger. It is the UI's answer to
// "is this real?" — every value is read from the API, never baked in.
export function TruthBadge({ meta }: { meta: Meta }) {
  return (
    <footer
      data-testid="truth-badge"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-chip border border-border bg-surface px-4 py-2 font-mono text-xs text-muted"
    >
      <span className="text-primary">Live from API</span>
      <span aria-hidden>·</span>
      <span>
        last event seq{" "}
        <span className="tabular text-text" data-testid="last-event-seq">
          {meta.last_event_seq}
        </span>
      </span>
      <span aria-hidden>·</span>
      <span>
        llm_mode <span className="text-text">{meta.llm_mode}</span>
      </span>
      <span aria-hidden>·</span>
      <span>
        chain{" "}
        {meta.chain_verified ? (
          <span className="text-ok">verified ✓</span>
        ) : (
          <span className="text-danger">
            broken ✗ (first broken index {meta.first_broken_index ?? "?"})
          </span>
        )}
      </span>
    </footer>
  );
}
