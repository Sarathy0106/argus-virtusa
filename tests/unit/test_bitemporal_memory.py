from datetime import UTC, datetime, timedelta

from services.memory.bitemporal import BitemporalMemoryStore
from services.memory.feedback import FeedbackLoopManager


def test_bitemporal_time_travel_queries():
    store = BitemporalMemoryStore()
    t0 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    t1 = datetime(2025, 6, 1, 0, 0, 0, tzinfo=UTC)

    # In January 2025: Customer risk category was LOW
    store.record_fact(
        subject="<ACCT_1001>",
        predicate="risk_tier",
        payload={"tier": "LOW"},
        valid_from=t0,
        valid_to=t1 - timedelta(seconds=1),
    )

    # In June 2025: Customer risk category upgraded to HIGH due to structuring
    store.record_fact(
        subject="<ACCT_1001>",
        predicate="risk_tier",
        payload={"tier": "HIGH"},
        valid_from=t1,
        valid_to=datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Time-travel query: What was customer tier in March 2025? -> Must be LOW
    march_query = store.query_as_of(
        "<ACCT_1001>", as_of_valid_time=datetime(2025, 3, 15, tzinfo=UTC)
    )
    assert len(march_query) == 1
    assert march_query[0].object["tier"] == "LOW"

    # Time-travel query: What was customer tier in October 2025? -> Must be HIGH
    oct_query = store.query_as_of(
        "<ACCT_1001>", as_of_valid_time=datetime(2025, 10, 15, tzinfo=UTC)
    )
    assert len(oct_query) == 1
    assert oct_query[0].object["tier"] == "HIGH"


def test_cryptographic_shredding_erasure():
    store = BitemporalMemoryStore()
    now = datetime.now(UTC)
    store.record_fact(
        subject="<ACCT_ERASE_ME>",
        predicate="kyc_document",
        payload={"doc_number": "DOC-999"},
        valid_from=now,
    )
    assert len(store.query_as_of("<ACCT_ERASE_ME>", as_of_valid_time=now)) == 1

    # Execute right-to-erase shredding
    store.crypto_shred_subject("<ACCT_ERASE_ME>")
    assert store.is_shredded("<ACCT_ERASE_ME>") is True

    # Subsequent queries must return empty
    assert len(store.query_as_of("<ACCT_ERASE_ME>", as_of_valid_time=now)) == 0


def test_analyst_feedback_loop_weight_tuning():
    loop = FeedbackLoopManager()
    assert loop.get_rule_weight("aml_structuring_window") == 1.0

    # Analyst marks an alert as FALSE POSITIVE -> down-weight rule
    loop.submit_feedback(
        case_id="CASE-01",
        decision_id="DEC-01",
        analyst_id="analyst_alice",
        verdict="FALSE_POSITIVE",
        notes="Customer provided business contract justification",
        rules_applied=["aml_structuring_window"],
    )
    assert loop.get_rule_weight("aml_structuring_window") < 1.0

    # Analyst confirms another alert as CONFIRMED_SUSPICIOUS -> strengthen rule
    loop.submit_feedback(
        case_id="CASE-02",
        decision_id="DEC-02",
        analyst_id="analyst_bob",
        verdict="CONFIRMED_SUSPICIOUS",
        notes="Confirmed mule account ring",
        rules_applied=["rapid_pass_through"],
    )
    assert loop.get_rule_weight("rapid_pass_through") > 1.0
