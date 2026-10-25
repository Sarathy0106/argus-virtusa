from datetime import UTC, datetime

from contracts.common import TransactionChannel
from contracts.transactions import Transaction
from services.cognition.clustering.clustering import AlertClusterer


def test_alert_clustering_compresses_linked_transactions():
    clusterer = AlertClusterer()
    now = datetime.now(UTC)

    # 4 Structuring Transactions between Account A and Account B using Device DEV_1
    for i in range(4):
        txn = Transaction(
            id=f"TXN-STRUC-{i}",
            account_token="<ACCT_A>",
            counterparty_token="<ACCT_B>",
            amount=49000.0 + (i * 100),
            timestamp=now,
            channel=TransactionChannel.UPI,
            device_id_token="<DEV_1>",
        )
        clusterer.add_alert(txn, evidence_ids=["aml_structuring_window"], tier="T1")

    # 1 Unrelated Alert between Account X and Account Y using Device DEV_2
    unrelated_txn = Transaction(
        id="TXN-UNRELATED-99",
        account_token="<ACCT_X>",
        counterparty_token="<ACCT_Y>",
        amount=50000.0,
        timestamp=now,
        channel=TransactionChannel.IMPS,
        device_id_token="<DEV_2>",
    )
    clusterer.add_alert(unrelated_txn, evidence_ids=["dormant_account_spike"], tier="T1")

    # 5 total alerts submitted
    cases = clusterer.cluster_into_cases()

    # Must be compressed into exactly 2 cases! (60% alert volume compression)
    assert len(cases) == 2

    # Case 1 should contain all 4 structuring transactions
    struc_case = next(c for c in cases if len(c.transaction_ids) == 4)
    assert "<ACCT_A>" in struc_case.linked_accounts
    assert "<ACCT_B>" in struc_case.linked_accounts
    assert "<DEV_1>" in struc_case.linked_devices
    assert struc_case.total_amount == 49000.0 + 49100.0 + 49200.0 + 49300.0
    assert "aml_structuring_window" in struc_case.evidence_types
    assert struc_case.case_graph["node_count"] > 0

    # Case 2 should contain the 1 unrelated transaction
    single_case = next(c for c in cases if len(c.transaction_ids) == 1)
    assert single_case.transaction_ids == ["TXN-UNRELATED-99"]
