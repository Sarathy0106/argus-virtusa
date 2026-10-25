from services.ingest.simulator import SyntheticTransactionGenerator


def test_synthetic_normal_transaction():
    gen = SyntheticTransactionGenerator(seed=123)
    txn = gen.generate_normal_transaction()
    assert txn.id.startswith("TXN-")
    assert txn.amount > 0
    assert txn.account_token.startswith("<ACCT_")
    assert txn.counterparty_token.startswith("<ACCT_")
    assert txn.account_token != txn.counterparty_token
    assert txn.metadata["pattern_type"] == "NORMAL"


def test_synthetic_structuring_burst():
    gen = SyntheticTransactionGenerator(seed=456)
    txns = gen.generate_structuring_burst()
    assert len(txns) == 4
    for t in txns:
        assert t.metadata["pattern_type"] == "STRUCTURING"
        # Each transaction should be just below 50,000 INR
        assert 45000.0 <= t.amount < 50000.0


def test_synthetic_mule_pass_through():
    gen = SyntheticTransactionGenerator(seed=789)
    txns = gen.generate_mule_pass_through()
    assert len(txns) == 4
    inflow = txns[0]
    outflows = txns[1:]
    assert inflow.metadata["pattern_type"] == "MULE_INFLOW"
    assert inflow.amount == 450000.0
    for out in outflows:
        assert out.metadata["pattern_type"] == "MULE_OUTFLOW"
        assert out.amount == 150000.0


def test_synthetic_ato_transaction():
    gen = SyntheticTransactionGenerator(seed=999)
    txn = gen.generate_ato_transaction()
    assert txn.metadata["pattern_type"] == "ACCOUNT_TAKEOVER"
    assert txn.device_id_token == "<DEV_UNKNOWN_NEW_HARDWARE>"
    assert txn.timestamp.hour == 3


def test_synthetic_adversarial_injection():
    gen = SyntheticTransactionGenerator(seed=101)
    txn = gen.generate_adversarial_injection()
    assert txn.metadata["pattern_type"] == "PROMPT_INJECTION_ATTACK"
    assert any(
        term in txn.narrative
        for term in ["Ignore", "Prompt Injection", "override", "Disregard", "IMPORTANT"]
    )


def test_synthetic_dataset_composition():
    gen = SyntheticTransactionGenerator(seed=202)
    dataset = gen.generate_dataset(total_count=100)
    assert len(dataset) >= 100
    types = {t.metadata.get("pattern_type") for t in dataset}
    assert "NORMAL" in types
    assert "STRUCTURING" in types
    assert "MULE_INFLOW" in types
    assert "ACCOUNT_TAKEOVER" in types
    assert "PROMPT_INJECTION_ATTACK" in types
