"""
Event bus for ARGUS v2 (B2).

An in-process asyncio pub/sub with an append-only event store. Every pipeline
stage start/end, agent message, objection, backtest tick and canary step emits an
event here. The SSE endpoint streams these to the UI with monotonic `seq` numbers
so the frontend can resume with `Last-Event-ID` and never miss an event.

The event store is the single source of the "live feel" in the UI — the frontend
renders these events, it does not invent them.
"""

from __future__ import annotations

import asyncio
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

# The event `type` values mirror the Part 3 SSE contract.
EventType = str


class ArgusEvent(BaseModel):
    seq: int
    ts: str
    case_id: str
    trace_id: str
    type: EventType
    stage: int | None = None
    agent: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    entry_hash: str | None = None


class EventBus:
    """Append-only, per-case monotonic-seq event store with asyncio fan-out.

    Thread-safe appends (the orchestrator may run in a worker thread) with
    asyncio subscriber queues for the SSE endpoint.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, list[ArgusEvent]] = defaultdict(list)
        self._subscribers: dict[str, set[asyncio.Queue[ArgusEvent]]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind the asyncio loop used to deliver events to SSE subscribers."""
        self._loop = loop

    def next_seq(self, case_id: str) -> int:
        with self._lock:
            return len(self._events[case_id]) + 1

    def emit(
        self,
        case_id: str,
        type: EventType,
        payload: dict[str, Any] | None = None,
        *,
        trace_id: str | None = None,
        stage: int | None = None,
        agent: str | None = None,
        entry_hash: str | None = None,
    ) -> ArgusEvent:
        """Append an event and fan it out to live subscribers. Safe to call from
        any thread."""
        with self._lock:
            seq = len(self._events[case_id]) + 1
            event = ArgusEvent(
                seq=seq,
                ts=datetime.now(timezone.utc).isoformat(),
                case_id=case_id,
                trace_id=trace_id or case_id,
                type=type,
                stage=stage,
                agent=agent,
                payload=payload or {},
                entry_hash=entry_hash,
            )
            self._events[case_id].append(event)
            subscribers = list(self._subscribers.get(case_id, ()))

        for q in subscribers:
            self._deliver(q, event)
        return event

    def _deliver(self, q: asyncio.Queue[ArgusEvent], event: ArgusEvent) -> None:
        loop = self._loop
        if loop is None:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass
            return
        loop.call_soon_threadsafe(self._safe_put, q, event)

    @staticmethod
    def _safe_put(q: asyncio.Queue[ArgusEvent], event: ArgusEvent) -> None:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass

    def history(self, case_id: str, after_seq: int = 0) -> list[ArgusEvent]:
        """Return stored events for a case with seq > after_seq (for Last-Event-ID
        resume)."""
        with self._lock:
            return [e for e in self._events[case_id] if e.seq > after_seq]

    def subscribe(self, case_id: str) -> asyncio.Queue[ArgusEvent]:
        q: asyncio.Queue[ArgusEvent] = asyncio.Queue(maxsize=1000)
        with self._lock:
            self._subscribers[case_id].add(q)
        return q

    def unsubscribe(self, case_id: str, q: asyncio.Queue[ArgusEvent]) -> None:
        with self._lock:
            self._subscribers[case_id].discard(q)

    def case_ids(self) -> list[str]:
        with self._lock:
            return list(self._events.keys())


_BUS: EventBus | None = None


def get_event_bus() -> EventBus:
    global _BUS
    if _BUS is None:
        _BUS = EventBus()
    return _BUS
