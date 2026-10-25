from datetime import datetime, timedelta, timezone

from contracts.common import TransactionChannel
from contracts.transactions import Transaction
from services.cognition.features.pipeline import FeaturePipeline


def test_feature_pipeline_sliding_window_and_graph_hops():
    pipeline = FeaturePipeline()
    base_time = datetime.now(timezone.utc)

    # Flag an account as mule/bad
    flagged_acct = "<ACCT_FLAGGED_999>"
    pipeline.record_flagged_account(flagged_acct)

    # Account A transfers to Flagged Account (Direct 1-hop link)
    t1 = Transaction(
        id="TXN-H1",
        account_token="<ACCT_A>",
        counterparty_token=flagged_acct,
        amount=10000.0,
        timestamp=base_time - timedelta(hours=2),
        channel=TransactionChannel.UPI,
        device_id_token="<DEV_1>",
    )
    pipeline.ingest_transaction(t1)

    # Account A performs structuring transfer just below 50k
    t2 = Transaction(
        id="TXN-H2",
        account_token="<ACCT_A>",
        counterparty_token="<ACCT_B>",
        amount=49000.0,
        timestamp=base_time - timedelta(minutes=30),
        channel=TransactionChannel.UPI,
        device_id_token="<DEV_1>",
    )
    pipeline.ingest_transaction(t2)

    # Current incoming transaction from Account A
    current_txn = Transaction(
        id="TXN-CUR",
        account_token="<ACCT_A>",
        counterparty_token="<ACCT_C>",
        amount=49500.0,
        timestamp=base_time,
        channel=TransactionChannel.UPI,
        device_id_token="<DEV_1>",
    )

    features = pipeline.extract_features(current_txn)

    # Assertions
    assert features["velocity_count_24h"] == 2  # t1 and t2
    assert features["velocity_count_1h"] == 1  # t2
    assert features["structuring_window_count_24h"] == 2  # t2 and current_txn both in [45k, 50k)
    assert features["graph_hop_distance_to_flagged"] == 1  # direct edge to flagged node
    assert features["amount"] == 49500.0
