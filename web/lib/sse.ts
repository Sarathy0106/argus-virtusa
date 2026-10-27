// EventSource wrapper for the case SSE stream. Reconnects with Last-Event-ID so
// no event is lost. Every event the UI renders comes from here (or a REST call).

export type ArgusEvent = {
  seq: number;
  ts: string;
  case_id: string;
  trace_id: string;
  type: string;
  stage?: number | null;
  agent?: string | null;
  payload: Record<string, unknown>;
  entry_hash?: string | null;
};

export function subscribeCaseEvents(
  caseId: string,
  onEvent: (ev: ArgusEvent) => void,
): () => void {
  const url = `/api/v2/cases/${caseId}/events`;
  const es = new EventSource(url);

  const handler = (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data) as ArgusEvent;
      onEvent(data);
    } catch {
      // ignore malformed frames (e.g. keepalive comments)
    }
  };

  // The gateway sets a per-event `event:` type; listen on the default message
  // channel plus the known event types.
  es.onmessage = handler;
  const types = [
    "stage.started",
    "stage.completed",
    "backtest.progress",
    "canary.step",
    "sprt.update",
    "breach.detected",
    "rollback.completed",
    "chaos.injected",
    "agent.message",
    "objection.raised",
  ];
  for (const t of types) es.addEventListener(t, handler as EventListener);

  return () => es.close();
}
