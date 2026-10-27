"""
Per-demo-step acceptance tests (Part 7). Each test maps to a demo step and
asserts REAL computed behaviour — not fabricated outputs.
"""

import io
from datetime import date
from pathlib import Path

import pytest

from contracts.rule_dsl import DSLAction, DSLCondition, DSLOperator, RuleDefinition
from services.agents.crypto import AgentKeyPair
from services.backtest.duck import DuckBacktestEngine
from services.gateway.upload import extract_text
from services.ledger.ledger import AuditLedger
from services.ledger.tamper import run_tamper_demo
from services.memory.rule_registry import BitemporalRuleRegistry
from services.orchestrator.v2_state_machine import (
    SAMPLE_BANK_PROFILE,
    RegulatoryRuleOrchestrator,
)
from services.rollout.engine import RolloutEngine
from services.traffic.chaos import ChaosController, ChaosKind
from services.traffic.stream import LiveTrafficStream

CIRCULARS = Path(__file__).resolve().parent.parent.parent / "data" / "circulars"


def _run(circular_file: str):
    text = (CIRCULARS / circular_file).read_text()
    orch = RegulatoryRuleOrchestrator()
    state = orch.run_pipeline(
        circular_id=circular_file[:2],
        circular_title=circular_file,
        circular_text=text,
        bank_profile=SAMPLE_BANK_PROFILE,
    )
    return orch, state


# ---------------------------------------------------------------------------
# Step 1: upload + chunking — PDF and MD give identical clause IDs
# ---------------------------------------------------------------------------
def test_step1_upload_chunking_pdf_md_identical():
    reportlab = pytest.importorskip("reportlab")
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    from services.agents.intake_agent import IntakeAgent

    md = (CIRCULARS / "C1_cash_deposit_edd.md").read_text()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 40
    for line in md.split("\n"):
        if y < 40:
            c.showPage()
            y = h - 40
        c.setFont("Helvetica", 9)
        c.drawString(40, y, line[:110])
        y -= 12
    c.showPage()
    c.save()

    pdf_text = extract_text("C1.pdf", buf.getvalue())
    md_text = extract_text("C1.md", md.encode())
    intake = IntakeAgent()
    pdf_ids = [cl.id for cl in intake.process_circular("C1", "C1", pdf_text)["clauses"]]
    md_ids = [cl.id for cl in intake.process_circular("C1", "C1", md_text)["clauses"]]
    assert pdf_ids == md_ids
    assert len(md_ids) > 1


# ---------------------------------------------------------------------------
# Step 2: applicability — C1 applicable, C2 not applicable, C4 injection ignored
# ---------------------------------------------------------------------------
def test_step2_applicability():
    _, c1 = _run("C1_cash_deposit_edd.md")
    assert len(c1.applicable_obligations) >= 1

    _, c2 = _run("C2_coop_nbfc_lending.md")
    assert len(c2.applicable_obligations) == 0  # co-op/NBFC only

    _, c4 = _run("C4_poisoned_circular.md")
    assert len(c4.obligations) == 0  # prompt-injection ignored


# ---------------------------------------------------------------------------
# Step 3/4: gap+conflict, Z3 counter-example, objection loop (<=3 iterations)
# ---------------------------------------------------------------------------
def test_step3_4_objection_loop_with_z3_counterexample():
    _, c1 = _run("C1_cash_deposit_edd.md")
    assert len(c1.bundles) >= 2  # one bundle per applicable obligation
    assert len(c1.objection_history) >= 1
    assert c1.iteration_count <= 3
    # At least one objection carries a real Z3 counter-example transaction.
    ces = [o.counter_example for o in c1.objection_history if o.counter_example]
    assert ces, "expected a Z3 counter-example"
    assert "amount" in ces[0]


def test_step4_c3_passes_without_loop():
    _, c3 = _run("C3_upi_merchant_limits.md")
    assert len(c3.applicable_obligations) >= 1
    assert len(c3.objection_history) == 0  # no objection loop for C3


# ---------------------------------------------------------------------------
# Step 5: real backtest — delta equals an independent DuckDB count, threshold-sensitive
# ---------------------------------------------------------------------------
def _rule(threshold: float) -> RuleDefinition:
    return RuleDefinition(
        rule_name="cash_edd",
        version="1.0.0",
        clause_id="C1",
        obligation_id="O1",
        description="cash edd",
        conditions=[
            DSLCondition(field="is_cash", operator=DSLOperator.EQ, value=True),
            DSLCondition(field="amount", operator=DSLOperator.GTE, value=threshold),
        ],
        action=DSLAction(outcome="HOLD", tier="T1", evidence_id="[C]"),
    )


def test_step5_backtest_real_and_threshold_sensitive():
    import duckdb

    eng = DuckBacktestEngine()
    r8 = eng.run(_rule(800000))
    r10 = eng.run(_rule(1000000))
    assert r8.total_rows == 500000
    assert r8.candidate_alerts != r10.candidate_alerts  # threshold changes result
    indep = (
        duckdb.connect()
        .execute(
            "select count(*) from read_parquet('data/parquet/transactions_500k.parquet') "
            "where is_cash and amount >= 800000"
        )
        .fetchone()[0]
    )
    assert indep == r8.candidate_alerts  # delta equals an independent count


# ---------------------------------------------------------------------------
# Step 6: approval security — one sig / same user / tamper all rejected
# ---------------------------------------------------------------------------
def test_step6_approval_security():
    from services.gateway import approvals as ap

    maker = AgentKeyPair(seed="argus.user.maker")
    checker = AgentKeyPair(seed="argus.user.checker")
    bh = ap.bundle_hash({"rule_name": "r", "version": "1.0.0"})
    payload = {"bundle_hash": bh, "rule_name": "r"}

    ap._APPROVALS.clear()
    key = ap._approval_key("CASE-T", bh)
    # Only maker signed -> rejected
    ap._APPROVALS[key] = {
        "rule_name": "r",
        "maker": {
            "user_id": "maker",
            "public_key": maker.public_key_hex,
            "signature": maker.sign_payload(payload),
        },
        "checker": None,
    }
    ok, _ = ap.verify_dual_signatures(bh, "r", case_id="CASE-T")
    assert ok is False

    # Same user twice -> rejected
    ap._APPROVALS[key]["checker"] = {
        "user_id": "maker",
        "public_key": maker.public_key_hex,
        "signature": maker.sign_payload(payload),
    }
    ok, _ = ap.verify_dual_signatures(bh, "r", case_id="CASE-T")
    assert ok is False

    # Distinct valid signers -> accepted
    ap._APPROVALS[key]["checker"] = {
        "user_id": "checker",
        "public_key": checker.public_key_hex,
        "signature": checker.sign_payload(payload),
    }
    ok, _ = ap.verify_dual_signatures(bh, "r", case_id="CASE-T")
    assert ok is True

    # Tamper after signing (verify against a different rule name) -> rejected
    ok, _ = ap.verify_dual_signatures(bh, "r_TAMPERED", case_id="CASE-T")
    assert ok is False


# ---------------------------------------------------------------------------
# Step 7: canary + SPRT — healthy reaches 100%, flood breaches
# ---------------------------------------------------------------------------
def _upi_rule() -> RuleDefinition:
    return RuleDefinition(
        rule_name="upi",
        version="1.2.0",
        clause_id="C2",
        obligation_id="O1",
        description="upi",
        conditions=[
            DSLCondition(field="input.amount", operator=DSLOperator.GTE, value=50000.0),
            DSLCondition(field="input.channel", operator=DSLOperator.EQ, value="UPI"),
        ],
        action=DSLAction(outcome="HOLD", tier="T2", evidence_id="[C]"),
    )


def test_step7_canary_sprt_healthy_and_flood():
    rule = _upi_rule()
    healthy = RolloutEngine(rule, 0.04, ChaosController(stream=LiveTrafficStream(seed=101)))
    r = healthy.run()
    assert r.reached_100 and not r.breached

    chaos = ChaosController(stream=LiveTrafficStream(seed=202))
    chaos.inject(ChaosKind.ALERT_FLOOD)
    flooded = RolloutEngine(rule, 0.04, chaos)
    r2 = flooded.run()
    assert r2.breached


# ---------------------------------------------------------------------------
# Step 8: replay + tamper — merkle inclusion verifies, tamper names broken index
# ---------------------------------------------------------------------------
def test_step8_ledger_merkle_tamper():
    led = AuditLedger()
    for i in range(20):
        led.append(event_type="DECISION", entity_id=f"D-{i}", signer="orch", payload={"i": i})
    assert led.verify_chain() is True
    proof = led.inclusion_proof(7)
    assert AuditLedger.verify_inclusion_proof(proof) is True

    rep = run_tamper_demo(led, 5)
    assert rep["before"]["verified"] is True
    assert rep["after"]["verified"] is False
    assert rep["after"]["first_broken_index"] == 6  # breaks at the next link
    assert led.verify_chain() is True  # live ledger untouched


def test_step8_bitemporal_asof():
    reg = BitemporalRuleRegistry()
    reg.seed_demo()
    before = reg.as_of("upi_high_risk_mcc_cap", date(2026, 10, 31))
    after = reg.as_of("upi_high_risk_mcc_cap", date(2026, 11, 1))
    assert before.version == "1.0.0"
    assert after.version == "2.0.0"


# ---------------------------------------------------------------------------
# all: SSE ordering — events have increasing seq, resume loses nothing
# ---------------------------------------------------------------------------
def test_all_sse_ordering_and_resume():
    from services.events.bus import EventBus

    bus = EventBus()
    for i in range(10):
        bus.emit("CASE-1", "stage.started", {"i": i}, stage=i + 1)
    history = bus.history("CASE-1")
    seqs = [e.seq for e in history]
    assert seqs == sorted(seqs) == list(range(1, 11))
    # Resume from seq 4 loses nothing after it.
    resumed = bus.history("CASE-1", after_seq=4)
    assert [e.seq for e in resumed] == list(range(5, 11))
