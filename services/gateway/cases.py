"""
Cases router (B2) — async pipeline runner + SSE event stream.

POST /api/v2/cases starts a pipeline run as a background task and returns a
case_id immediately. The run emits events (stage start/end, backtest progress,
etc.) to the event bus. GET /api/v2/cases/{id}/events streams them as SSE with
Last-Event-ID resume support.

Every value streamed comes from real computation inside the orchestrator and the
DuckDB backtest — nothing here is fabricated.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, File, Form, Header, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.backtest.duck import DuckBacktestEngine
from services.events.bus import get_event_bus
from services.gateway.upload import UnsupportedUploadError, extract_text
from services.orchestrator.v2_state_machine import (
    SAMPLE_BANK_PROFILE,
    SAMPLE_CIRCULAR_TEXT,
    RegulatoryRuleOrchestrator,
)

router = APIRouter(prefix="/api/v2/cases", tags=["ARGUS v2 Cases"])

# In-memory case registry. A case holds its orchestrator + final state snapshot.
_CASES: dict[str, dict[str, Any]] = {}


def get_case_record(case_id: str) -> dict[str, Any] | None:
    """Accessor for other routers (approvals/deploy/audit)."""
    return _CASES.get(case_id)


class CreateCaseRequest(BaseModel):
    preset_id: str | None = None
    circular_id: str | None = None
    circular_title: str | None = None
    circular_text: str | None = None


def _run_pipeline_blocking(case_id: str, req: CreateCaseRequest) -> None:
    """Run the pipeline to approval, emitting real events as stages complete.

    Runs in a worker thread (via asyncio.to_thread) so the event loop stays free
    to serve SSE subscribers.
    """
    bus = get_event_bus()
    orch = RegulatoryRuleOrchestrator()
    _CASES[case_id]["orchestrator"] = orch

    text = req.circular_text or SAMPLE_CIRCULAR_TEXT
    circ_id = req.circular_id or "RBI-2024-118"
    circ_title = req.circular_title or "Enhanced Risk Management for UPI Transactions"

    def on_stage(stage: int, name: str, phase: str, payload: dict[str, Any]) -> None:
        bus.emit(
            case_id,
            f"stage.{phase}",
            {"stage_name": name, **payload},
            stage=stage,
        )

    # Hook the orchestrator's stage logger to the bus.
    orch.on_event = lambda **kw: bus.emit(case_id, **kw)  # type: ignore[attr-defined]

    try:
        bus.emit(case_id, "stage.started", {"stage_name": "CIRCULAR_INTAKE"}, stage=1)
        state = orch.run_pipeline(
            circular_text=text,
            bank_profile=SAMPLE_BANK_PROFILE,
            circular_id=circ_id,
            circular_title=circ_title,
        )

        # Real backtest over the 500k dataset with progress events (B5).
        if state.rule_definition is not None:
            engine = DuckBacktestEngine()

            def progress(processed: int, total: int, running_alerts: int) -> None:
                bus.emit(
                    case_id,
                    "backtest.progress",
                    {
                        "processed": processed,
                        "total": total,
                        "running_alert_delta": running_alerts,
                    },
                    stage=5,
                )

            result = engine.run(state.rule_definition, progress_cb=progress)
            _CASES[case_id]["backtest"] = result.model_dump()
            bus.emit(
                case_id,
                "stage.completed",
                {
                    "stage_name": "BACKTESTING",
                    "total_rows": result.total_rows,
                    "candidate_alerts": result.candidate_alerts,
                    "baseline_alerts": result.baseline_alerts,
                    "delta_alerts": result.delta_alerts,
                },
                stage=5,
            )

        _CASES[case_id]["state"] = orch.state
        _CASES[case_id]["status"] = "COMPLETED"
        bus.emit(
            case_id,
            "stage.completed",
            {"stage_name": state.stage_name, "current_stage": state.current_stage},
            stage=state.current_stage,
        )
    except Exception as exc:  # noqa: BLE001 - surface failures as events, not crashes
        _CASES[case_id]["status"] = "FAILED"
        _CASES[case_id]["error"] = str(exc)
        bus.emit(case_id, "stage.completed", {"error": str(exc), "failed": True})


PRESETS: dict[str, str] = {}


def _load_presets() -> dict[str, str]:
    """Load the four bundled circulars (C1-C4) as presets from data/circulars."""
    global PRESETS
    if PRESETS:
        return PRESETS
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent / "data" / "circulars"
    mapping = {
        "C1": "C1_cash_deposit_edd.md",
        "C2": "C2_coop_nbfc_lending.md",
        "C3": "C3_upi_merchant_limits.md",
        "C4": "C4_poisoned_circular.md",
    }
    for pid, fname in mapping.items():
        fp = root / fname
        if fp.exists():
            PRESETS[pid] = fp.read_text(encoding="utf-8")
    return PRESETS


@router.get("/presets/list")
async def list_presets() -> dict[str, Any]:
    presets = _load_presets()
    return {"presets": [{"id": pid, "title": pid} for pid in presets]}


@router.post("")
async def create_case(
    request: Request,
    file: UploadFile | None = File(default=None),
    preset_id: str | None = Form(default=None),
    circular_id: str | None = Form(default=None),
    circular_title: str | None = Form(default=None),
    circular_text: str | None = Form(default=None),
) -> dict[str, Any]:
    """
    Start a pipeline run and return case_id immediately (B2 + B3).

    Accepts either multipart (a PDF/MD/TXT `file`, or form fields) OR a JSON body
    with the same fields. An uploaded PDF is text-extracted via pdfplumber and run
    through the same Airlock + clause chunker as presets.
    """
    req = CreateCaseRequest(
        preset_id=preset_id,
        circular_id=circular_id,
        circular_title=circular_title,
        circular_text=circular_text,
    )

    # JSON body fallback (no multipart fields present).
    if file is None and not any([preset_id, circular_text]):
        ctype = request.headers.get("content-type", "")
        if ctype.startswith("application/json"):
            body = await request.json()
            req = CreateCaseRequest(**body)

    # Resolve the circular text from the various input modes.
    if file is not None:
        content = await file.read()
        try:
            text = extract_text(file.filename or "upload", content)
        except UnsupportedUploadError as exc:
            return {"error": str(exc)}, 400
        req.circular_text = text
        req.circular_title = req.circular_title or (file.filename or "Uploaded circular")
        req.circular_id = req.circular_id or f"UP-{uuid.uuid4().hex[:6]}"
    elif req.preset_id:
        presets = _load_presets()
        if req.preset_id in presets:
            req.circular_text = presets[req.preset_id]
            req.circular_id = req.circular_id or req.preset_id
            req.circular_title = req.circular_title or req.preset_id

    case_id = f"CASE-{uuid.uuid4().hex[:10]}"
    _CASES[case_id] = {"status": "RUNNING", "orchestrator": None, "state": None}
    get_event_bus().bind_loop(asyncio.get_running_loop())
    asyncio.create_task(asyncio.to_thread(_run_pipeline_blocking, case_id, req))
    return {"case_id": case_id, "status": "RUNNING"}


@router.get("")
async def list_cases() -> dict[str, Any]:
    return {
        "cases": [
            {"case_id": cid, "status": c.get("status")}
            for cid, c in _CASES.items()
        ]
    }


@router.get("/{case_id}")
async def get_case(case_id: str) -> dict[str, Any]:
    case = _CASES.get(case_id)
    if not case:
        return {"case_id": case_id, "status": "UNKNOWN"}
    state = case.get("state")
    bundle = None
    b_hash = None
    bundles = []
    if state is not None:
        bundles = state.bundles
        if state.rule_definition is not None:
            from services.gateway.approvals import bundle_hash

            bundle = state.rule_definition.model_dump(mode="json")
            b_hash = bundle_hash(bundle)
    return {
        "case_id": case_id,
        "status": case.get("status"),
        "backtest": case.get("backtest"),
        "error": case.get("error"),
        "bundle_count": len(bundles),
        "selected_bundle": bundle,
        "bundle_hash": b_hash,
        "rule_name": bundle.get("rule_name") if bundle else None,
    }


@router.get("/{case_id}/detail")
async def get_case_detail(case_id: str) -> dict[str, Any]:
    """Full case detail for the UI pages: obligations (with applicability),
    policy mapping, and per-obligation bundles with objections. All derived from
    the real pipeline state."""
    case = _CASES.get(case_id)
    if not case or case.get("state") is None:
        return {"case_id": case_id, "status": case.get("status") if case else "UNKNOWN"}
    state = case["state"]

    obligations = [
        {
            "id": o.id,
            "clause_id": o.clause_id,
            "actor": o.actor,
            "rule_ref": o.rule_ref,
            "condition": o.condition_json,
            "action": o.action_json,
            "deadline": o.deadline,
            "applicability": o.applicability_status.value,
            "rationale": o.applicability_rationale,
        }
        for o in state.obligations
    ]
    mappings = []
    if state.policy_mapping:
        for m in state.policy_mapping.mappings:
            mappings.append(
                {
                    "obligation_id": m.obligation_id,
                    "clause_id": m.clause_id,
                    "conflict_type": getattr(m.conflict_type, "value", str(m.conflict_type)),
                    "existing_rule_ref": m.existing_rule_ref,
                    "description": m.description,
                    "suggested_resolution": m.suggested_resolution,
                }
            )
    return {
        "case_id": case_id,
        "status": case.get("status"),
        "circular_id": state.circular_id,
        "clause_count": len(state.clauses),
        "obligations": obligations,
        "mappings": mappings,
        "bundles": [
            {k: v for k, v in b.items() if not k.startswith("_")} for b in state.bundles
        ],
        "selected_bundle_index": state.selected_bundle_index,
    }


@router.get("/{case_id}/events")
async def stream_events(
    case_id: str,
    request: Request,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """SSE stream of case events with Last-Event-ID resume."""
    bus = get_event_bus()
    bus.bind_loop(asyncio.get_running_loop())
    after = 0
    if last_event_id and last_event_id.isdigit():
        after = int(last_event_id)

    async def event_gen():
        # Replay anything already recorded beyond the resume point.
        for ev in bus.history(case_id, after_seq=after):
            yield _format_sse(ev)
        queue = bus.subscribe(case_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=15.0)
                    # Skip anything already replayed.
                    if ev.seq <= after:
                        continue
                    yield _format_sse(ev)
                except TimeoutError:
                    # Heartbeat comment keeps the connection alive.
                    yield ": keepalive\n\n"
        finally:
            bus.unsubscribe(case_id, queue)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _format_sse(ev) -> str:
    return f"id: {ev.seq}\nevent: {ev.type}\ndata: {json.dumps(ev.model_dump())}\n\n"
