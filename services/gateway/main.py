"""
ARGUS v2 FastAPI API Gateway.

The gateway is the ONLY place the regulatory pipeline runs. The Next.js frontend
renders exclusively what this API computes.

R0 (Triage) scope applied here:
  * v1 fraud/AML routes (/api/v1/*) and the in-process ArgusOrchestrator were
    retired to legacy/ — they are gone from this gateway.
  * CORS is restricted to the configured web origin (no allow_origins=['*']).
  * The Vue static mount at '/' was removed; the Next.js app owns the frontend.
  * A real /api/v2/meta endpoint reports live llm_mode, ledger chain status and
    last event seq — no fabricated values.

Later work orders (B1-B14) layer the event bus, real backtest, SPRT, measured
rollback, real replay, bitemporal memory and verified A2A onto this base.
"""

import os
import time
from datetime import datetime, timezone

import yaml
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.config import get_settings
from services.events.bus import get_event_bus
from services.gateway.approvals import router as approvals_router
from services.gateway.cases import router as cases_router
from services.gateway.memory_routes import router as memory_router
from services.gateway.meta import ollama_reachable, probe_llm_mode
from services.gateway.rollout_routes import router as rollout_router
from services.ledger.ledger import AuditChainIntegrityError
from services.orchestrator.v2_state_machine import (
    SAMPLE_BANK_PROFILE,
    SAMPLE_CIRCULAR_TEXT,
)
from services.orchestrator.v2_state_machine import (
    RegulatoryRuleOrchestrator as V2StateMachine,
)

settings = get_settings()

app = FastAPI(
    title="ARGUS v2 API Gateway",
    description="Regulatory Circular -> Live Rule Engine API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# The frontend origin is the ONLY allowed cross-origin caller. No wildcard.
WEB_ORIGIN = os.environ.get("ARGUS_WEB_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEB_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single v2 orchestrator instance. Pipeline bootstrap is best-effort so the API
# can boot (and /meta can answer) even if a stage is mid-rebuild.
v2_orchestrator = V2StateMachine()
try:
    v2_orchestrator.run_pipeline(
        circular_text=SAMPLE_CIRCULAR_TEXT,
        bank_profile=SAMPLE_BANK_PROFILE,
    )
    v2_orchestrator.maker_signoff(maker_id="maker_compliance_4492")
    v2_orchestrator.checker_signoff(checker_id="checker_risk_vp_9104")
    v2_orchestrator.activate_shadow()
    v2_orchestrator.ramp_canary(traffic_pct=10.0)
except Exception as exc:  # noqa: BLE001 - bootstrap must never block boot
    print(f"Warning: initial v2 pipeline bootstrap did not complete: {exc}")


# ---------------------------------------------------------------------------
# Versioned v2 router
# ---------------------------------------------------------------------------
v2 = APIRouter(prefix="/api/v2", tags=["ARGUS v2"])


def _chain_status() -> tuple[bool, int, int | None]:
    """Return (verified, count, first_broken_index) read from the live ledger."""
    ledger = v2_orchestrator.ledger
    count = ledger.count()
    try:
        verified = ledger.verify_chain()
        return verified, count, None
    except AuditChainIntegrityError as exc:
        # The message names the first broken sequence; surface it honestly.
        broken = None
        for token in str(exc).split():
            stripped = token.strip(":.,;")
            if stripped.isdigit():
                broken = int(stripped)
                break
        return False, count, broken


@app.get("/.well-known/agent.json", tags=["A2A"])
def agent_directory():
    """A2A agent directory (B13): published agent cards with their public keys and
    skills. A forged/modified envelope is rejected by the broker on receipt."""
    cards = []
    for card in v2_orchestrator.broker.registered_agents.values():
        cards.append(
            {
                "agent_id": card.agent_id,
                "name": card.name,
                "version": card.version,
                "public_key": card.public_key,
                "skills": [s.name for s in card.skills],
            }
        )
    return {"agents": cards, "transport": "in_process_signed_a2a"}


@app.get("/health", tags=["System"])
def health_check():
    """Liveness probe. Reports only process-level truth."""
    return {
        "status": "HEALTHY",
        "service": "ARGUS v2 API Gateway",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@v2.get("/meta")
def get_meta():
    """
    Live system metadata for the UI truth badge. Every field is measured now:
      * llm_mode is a real probe of the Ollama runtime.
      * chain_verified / first_broken_index come from AuditLedger.verify_chain().
      * last_event_seq is the real ledger length.
    """
    verified, count, broken = _chain_status()
    return {
        "service": "argus-v2-gateway",
        "version": "2.0.0",
        "llm_mode": probe_llm_mode(),
        "ollama_reachable": ollama_reachable(),
        "chain_verified": verified,
        "first_broken_index": broken,
        "last_event_seq": count,
        "web_origin": WEB_ORIGIN,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


def serialize_v2_state():
    s = v2_orchestrator.state
    if not s:
        return {}

    mappings = s.policy_mapping.mappings if s.policy_mapping else []
    gaps = [
        m
        for m in mappings
        if getattr(m.conflict_type, "value", str(m.conflict_type)) == "GAP"
    ]
    overlaps = [
        m
        for m in mappings
        if getattr(m.conflict_type, "value", str(m.conflict_type)) == "OVERLAP"
    ]

    yaml_str = (
        yaml.dump(s.rule_definition.model_dump(mode="json"), sort_keys=False)
        if s.rule_definition
        else ""
    )

    dep_stage = (
        s.deployment_stage.value
        if hasattr(s.deployment_stage, "value")
        else str(s.deployment_stage)
    )
    canary_val = s.canary_metrics[-1].traffic_pct if s.canary_metrics else 0.0

    return {
        "circular_id": s.circular_id,
        "current_stage": s.current_stage,
        "deployment_stage": dep_stage,
        "obligations_count": len(s.obligations),
        "applicable_count": len(s.applicable_obligations),
        "gaps": len(gaps),
        "overlaps": len(overlaps),
        "rule_dsl_yaml": yaml_str,
        "rego_code": s.compiled_rego or "",
        "test_code": s.compiled_tests or "",
        "maker_signed": s.approval_token is not None,
        "checker_signed": s.approval_token is not None,
        "validation_passed": s.validation_report.passed if s.validation_report else None,
        "canary_pct": canary_val,
        "rollback_recorded": s.rollback_record is not None,
    }


@v2.get("/state")
def get_v2_state():
    """Current snapshot of the 10-stage pipeline (serialized from live state)."""
    return serialize_v2_state()


class IngestCircularRequest(BaseModel):
    circular_id: str
    circular_title: str
    circular_text: str


@v2.post("/run-full-pipeline")
def run_v2_full_pipeline():
    """Re-execute the full pipeline with dual sign-off and canary ramp."""
    global v2_orchestrator
    v2_orchestrator = V2StateMachine()
    v2_orchestrator.run_pipeline(
        circular_text=SAMPLE_CIRCULAR_TEXT,
        bank_profile=SAMPLE_BANK_PROFILE,
    )
    v2_orchestrator.maker_signoff(maker_id="maker_compliance_4492")
    v2_orchestrator.checker_signoff(checker_id="checker_risk_vp_9104")
    v2_orchestrator.activate_shadow()
    v2_orchestrator.ramp_canary(traffic_pct=10.0)
    return serialize_v2_state()


@v2.get("/audit/ledger")
def get_v2_audit_ledger():
    """Return the live SHA-256 hash-chained ledger blocks and real integrity status."""
    verified, count, broken = _chain_status()
    blocks = []
    for i in range(1, count + 1):
        b = v2_orchestrator.ledger.get_by_seq(i)
        if b:
            blocks.append(
                {
                    "seq": b.seq,
                    "prev_hash": b.prev_hash,
                    "block_hash": b.verify_hash(),
                    "event_type": b.event_type,
                    "entity_id": b.entity_id,
                    "signer": b.signer,
                    "recorded_at": b.recorded_at.isoformat(),
                }
            )
    return {
        "total_blocks": count,
        "integrity_verified": verified,
        "first_broken_index": broken,
        "blocks": blocks,
    }


@v2.post("/rollback")
def trigger_v2_rollback():
    """
    Trigger a rollback and return the MEASURED duration (monotonic clock).
    NOTE: a fully measured breach->rollback saga is delivered in B10; this
    endpoint already returns a real wall-time measurement of the swap.
    """
    start_t = time.perf_counter()
    v2_orchestrator.emergency_rollback(
        reason="Manual emergency trigger (operator override)"
    )
    duration_ms = (time.perf_counter() - start_t) * 1000.0
    stage = v2_orchestrator.state.deployment_stage
    return {
        "status": "ROLLED_BACK",
        "rollback_ms": round(duration_ms, 3),
        "stage": stage.value if hasattr(stage, "value") else str(stage),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.on_event("startup")
async def _bind_event_loop() -> None:
    # Bind the running loop so the event bus can deliver to SSE subscribers from
    # worker threads.
    import asyncio

    get_event_bus().bind_loop(asyncio.get_running_loop())


app.include_router(v2)
app.include_router(cases_router)
app.include_router(approvals_router)
app.include_router(rollout_router)
app.include_router(memory_router)
