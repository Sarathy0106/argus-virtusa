"""
ARGUS UI Test Suite
Tests: seed data correctness, PII tokenization scanning, ledger chain integrity, offline client.
"""
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Ensure repo root and ui root are on path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
UI_ROOT = Path(__file__).resolve().parent.parent
for p in [str(REPO_ROOT), str(UI_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

from ui.data.seed import (
    SEED_CASES, SEED_LEDGER, SEED_TRANSACTIONS,
    canonical_json_hash, build_seed_cases, build_seed_ledger, build_seed_transactions,
    REGULATION_CLAUSES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _recompute_block_hash(block: dict) -> str:
    prev_hash = block.get("prev_hash", "0" * 64)
    payload_hash = canonical_json_hash(block.get("payload", {}))
    chain_input = (
        f"{prev_hash}{payload_hash}"
        f"{block.get('event_type','')}"
        f"{block.get('entity_id','')}"
        f"{block.get('signer','')}"
        f"{block.get('recorded_at','')}"
    )
    return hashlib.sha256(chain_input.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Seed Data Tests
# ---------------------------------------------------------------------------
class TestSeedCases:
    def test_exactly_two_cases(self):
        cases = build_seed_cases()
        assert len(cases) == 2, f"Expected 2 cases, got {len(cases)}"

    def test_mule_case_id(self):
        cases = {c["case_id"]: c for c in build_seed_cases()}
        assert "CASE-MULE-8821" in cases, "CASE-MULE-8821 not found"

    def test_struc_case_id(self):
        cases = {c["case_id"]: c for c in build_seed_cases()}
        assert "CASE-STRUC-1049" in cases, "CASE-STRUC-1049 not found"

    def test_mule_amount(self):
        cases = {c["case_id"]: c for c in build_seed_cases()}
        assert cases["CASE-MULE-8821"]["total_amount"] == 900_000.0

    def test_struc_amount(self):
        cases = {c["case_id"]: c for c in build_seed_cases()}
        assert cases["CASE-STRUC-1049"]["total_amount"] == 197_700.0

    def test_mule_tier(self):
        cases = {c["case_id"]: c for c in build_seed_cases()}
        assert cases["CASE-MULE-8821"]["primary_tier"] == "T2"

    def test_struc_tier(self):
        cases = {c["case_id"]: c for c in build_seed_cases()}
        assert cases["CASE-STRUC-1049"]["primary_tier"] == "T1"

    def test_mule_has_shap_rows(self):
        cases = {c["case_id"]: c for c in build_seed_cases()}
        mule = cases["CASE-MULE-8821"]
        assert "shap_rows" in mule
        assert len(mule["shap_rows"]) >= 4

    def test_mule_shap_rapid_pass_through(self):
        cases = {c["case_id"]: c for c in build_seed_cases()}
        mule = cases["CASE-MULE-8821"]
        features = [row["Feature"] for row in mule["shap_rows"]]
        assert "rapid_pass_through_delta" in features

    def test_mule_graph_has_device_node(self):
        cases = {c["case_id"]: c for c in build_seed_cases()}
        mule = cases["CASE-MULE-8821"]
        node_types = [n["type"] for n in mule["case_graph"]["nodes"]]
        assert "DEVICE" in node_types

    def test_mule_graph_node_count(self):
        cases = {c["case_id"]: c for c in build_seed_cases()}
        mule = cases["CASE-MULE-8821"]
        assert mule["case_graph"]["node_count"] == 10

    def test_case_required_fields(self):
        required = ["case_id", "title", "primary_tier", "transaction_ids",
                    "total_amount", "linked_accounts", "linked_devices",
                    "evidence_types", "case_graph"]
        for case in build_seed_cases():
            for field in required:
                assert field in case, f"Missing field '{field}' in case {case.get('case_id')}"


# ---------------------------------------------------------------------------
# PII Tokenization Scanning Tests
# ---------------------------------------------------------------------------
class TestPIITokenization:
    """
    Strict Airlock Test: verifies no raw PII appears in seed data or any
    returned field. All identifiers must use <TOKEN> or <ALIAS> format.
    """

    PII_PATTERNS = [
        # Raw Aadhaar (12 digits)
        r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        # Raw PAN (10 alphanumeric)
        r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        # Raw mobile (Indian, 10 digits starting 6-9)
        r"\b[6-9]\d{9}\b",
        # Raw email
        r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[a-zA-Z]{2,}",
    ]

    def _scan_for_pii(self, text: str) -> list[str]:
        import re
        found = []
        for pattern in self.PII_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                found.extend(matches)
        return found

    def _flatten(self, obj, path="") -> list[tuple[str, str]]:
        """Flatten nested dict/list into (path, str_value) pairs."""
        results = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                results.extend(self._flatten(v, f"{path}.{k}"))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                results.extend(self._flatten(item, f"{path}[{i}]"))
        elif isinstance(obj, str):
            results.append((path, obj))
        elif obj is not None:
            results.append((path, str(obj)))
        return results

    def test_case_accounts_are_tokenized(self):
        """All account identifiers must be in <TOKEN> format, no raw account numbers."""
        import re
        raw_acct_pattern = re.compile(r"\b\d{9,18}\b")  # bare digit bank account numbers
        for case in SEED_CASES:
            for acct in case.get("linked_accounts", []):
                assert not raw_acct_pattern.search(acct), (
                    f"Possible raw account number found: {acct} in case {case['case_id']}"
                )

    def test_transaction_ids_no_pii(self):
        """Transaction IDs must not contain raw PII."""
        for case in SEED_CASES:
            for txn_id in case.get("transaction_ids", []):
                pii = self._scan_for_pii(txn_id)
                assert not pii, f"PII found in transaction_id '{txn_id}': {pii}"

    def test_seed_transactions_tokens_not_raw(self):
        """Seed transactions must use tokenised fields."""
        for txn in SEED_TRANSACTIONS:
            for field in ["account_token", "counterparty_token", "device_id_token"]:
                val = txn.get(field, "")
                if val:
                    pii = self._scan_for_pii(str(val))
                    assert not pii, f"PII found in {field}='{val}': {pii}"

    def test_clause_text_no_pii_leakage(self):
        """Regulation clause text must not contain any real PAN/Aadhaar samples."""
        for clause in REGULATION_CLAUSES:
            pii = self._scan_for_pii(clause.get("clause_text", ""))
            assert not pii, f"PII found in clause {clause['id']}: {pii}"

    def test_no_raw_email_in_seed(self):
        """No raw email addresses should exist in any seed case field."""
        import re
        email_pattern = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[a-zA-Z]{2,}")
        for case in SEED_CASES:
            flat = self._flatten(case)
            for path, val in flat:
                if email_pattern.search(val):
                    # Signer format "maker:alice|checker:bob" is not email
                    if "@" not in val or "." not in val.split("@")[-1]:
                        continue
                    pytest.fail(f"Possible email PII at {path}: {val}")

    def test_adversarial_injection_not_in_seed_cases(self):
        """Seed cases must not contain prompt injection strings."""
        injection_markers = [
            "SYSTEM NOTE", "Ignore previous rules", "bypass_sanctions",
            "system prompt", "vault encryption key",
        ]
        for case in SEED_CASES:
            flat = self._flatten(case)
            for path, val in flat:
                for marker in injection_markers:
                    assert marker not in val, (
                        f"Injection marker '{marker}' found at {path}: {val[:80]}"
                    )


# ---------------------------------------------------------------------------
# Audit Ledger Integrity Tests
# ---------------------------------------------------------------------------
class TestAuditLedger:
    def test_ledger_has_genesis_block(self):
        ledger = build_seed_ledger()
        assert len(ledger) >= 1
        assert ledger[0]["seq"] == 1

    def test_genesis_prev_hash_is_zero(self):
        ledger = build_seed_ledger()
        assert ledger[0]["prev_hash"] == "0" * 64

    def test_chain_forward_links(self):
        ledger = build_seed_ledger()
        for i in range(1, len(ledger)):
            assert ledger[i]["prev_hash"] == ledger[i - 1]["block_hash"], (
                f"Chain break at block {ledger[i]['seq']}: "
                f"prev_hash {ledger[i]['prev_hash'][:16]} != "
                f"block_hash of block {i}: {ledger[i-1]['block_hash'][:16]}"
            )

    def test_all_block_hashes_recompute(self):
        ledger = build_seed_ledger()
        for block in ledger:
            expected = _recompute_block_hash(block)
            assert block["block_hash"] == expected, (
                f"Hash mismatch for block {block['seq']}: "
                f"stored={block['block_hash'][:16]}, computed={expected[:16]}"
            )

    def test_block_hash_is_hex_64(self):
        ledger = build_seed_ledger()
        for block in ledger:
            h = block["block_hash"]
            assert len(h) == 64, f"Block {block['seq']} hash wrong length: {len(h)}"
            assert all(c in "0123456789abcdef" for c in h), (
                f"Block {block['seq']} hash not lowercase hex: {h[:16]}"
            )

    def test_decision_block_present(self):
        ledger = build_seed_ledger()
        event_types = [b["event_type"] for b in ledger]
        assert "DECISION_RECORDED" in event_types

    def test_case_resolved_block_present(self):
        ledger = build_seed_ledger()
        event_types = [b["event_type"] for b in ledger]
        assert "CASE_RESOLVED_CONFIRMED" in event_types

    def test_rule_published_block_present(self):
        ledger = build_seed_ledger()
        event_types = [b["event_type"] for b in ledger]
        assert "RULE_BUNDLE_PUBLISHED" in event_types

    def test_tamper_detection(self):
        """Mutating a payload must produce a hash mismatch."""
        ledger = build_seed_ledger()
        tampered = dict(ledger[1])
        tampered["payload"] = dict(tampered["payload"])
        tampered["payload"]["outcome"] = "ALLOW"  # tamper
        recomputed = _recompute_block_hash(tampered)
        assert recomputed != tampered["block_hash"], (
            "Tamper not detected — hash should differ after payload mutation"
        )


# ---------------------------------------------------------------------------
# Seed Transactions Tests
# ---------------------------------------------------------------------------
class TestSeedTransactions:
    def test_count(self):
        txns = build_seed_transactions(150)
        assert len(txns) == 150

    def test_ids_unique(self):
        txns = build_seed_transactions(150)
        ids = [t["id"] for t in txns]
        assert len(ids) == len(set(ids)), "Transaction IDs must be unique"

    def test_amounts_positive(self):
        txns = build_seed_transactions(150)
        for t in txns:
            assert t["amount"] > 0, f"Negative amount in {t['id']}"

    def test_currency_inr(self):
        txns = build_seed_transactions(150)
        for t in txns:
            assert t["currency"] == "INR"

    def test_deterministic(self):
        """Two calls with same seed must return identical datasets."""
        txns1 = build_seed_transactions(150)
        txns2 = build_seed_transactions(150)
        assert txns1[0]["id"] == txns2[0]["id"]
        assert txns1[-1]["id"] == txns2[-1]["id"]
        assert txns1[42]["amount"] == txns2[42]["amount"]


# ---------------------------------------------------------------------------
# Offline Client Tests
# ---------------------------------------------------------------------------
class TestOfflineClient:
    """Tests the offline fallback behaviour of ui/services/client.py."""

    def test_get_cases_offline_returns_two(self, monkeypatch):
        """When API is not reachable, get_cases returns seed data (2 items)."""
        import ui.services.client as client
        monkeypatch.setattr(client, "_api_reachable", False)
        cases = client.get_cases()
        assert len(cases) == 2

    def test_get_ledger_offline_returns_blocks(self, monkeypatch):
        import ui.services.client as client
        monkeypatch.setattr(client, "_api_reachable", False)
        blocks = client.get_ledger_blocks()
        assert len(blocks) >= 4

    def test_compliance_query_keyword_match(self, monkeypatch):
        import ui.services.client as client
        monkeypatch.setattr(client, "_api_reachable", False)
        result = client.compliance_query("KYC updation frequency high risk", date.today())
        assert not result["abstained"], "KYC query should match in-force clause"
        assert "RBI-KYC-C23" in result.get("answer", "")

    def test_compliance_query_expired_abstains(self, monkeypatch):
        """Legacy cash CTR rule expired in 2023 — a query matching ONLY the expired clause should
        abstain when as_of_date is today (beyond valid_to 2023-03-31)."""
        import ui.services.client as client
        monkeypatch.setattr(client, "_api_reachable", False)
        # Keywords "old" and "legacy" appear ONLY in the expired clause (RBI-OLD-AML-C04).
        # This ensures no in-force clause also matches, so the system must abstain.
        result = client.compliance_query("old legacy superseded rule", date.today())
        assert result["abstained"], (
            "Query matching only an expired clause should cause abstention. "
            f"Got: abstained={result['abstained']}, sources={[s.get('id') for s in result.get('sources', [])]}"
        )

    def test_compile_rule_offline_returns_rego(self, monkeypatch):
        import ui.services.client as client
        monkeypatch.setattr(client, "_api_reachable", False)
        obligation = {
            "id": "OBL-TEST-01",
            "rule_ref": "test_rule",
            "clause_id": "TEST-CLAUSE",
            "condition_json": {"threshold_amount": 50000, "channel": "UPI"},
            "action_json": {"action": "HOLD", "tier": "T1"},
        }
        result = client.compile_rule(obligation)
        assert "rego_code" in result
        assert "package argus.compiled.test_rule" in result["rego_code"]
        assert "test_code" in result
        assert "test_rule_hit" in result["test_code"]

    def test_simulate_rule_offline(self, monkeypatch):
        import ui.services.client as client
        monkeypatch.setattr(client, "_api_reachable", False)
        obligation = {
            "condition_json": {"threshold_amount": 800000, "channel": "RTGS"},
            "action_json": {"action": "HOLD", "tier": "T2"},
        }
        txns = client.get_transactions()
        result = client.simulate_rule(obligation, txns)
        assert "total_txns_analyzed" in result
        assert result["total_txns_analyzed"] == 150
        assert "new_alert_count" in result

    def test_is_live_false_when_api_down(self, monkeypatch):
        import ui.services.client as client
        monkeypatch.setattr(client, "_api_reachable", False)
        assert not client.is_live()


# ---------------------------------------------------------------------------
# Regulation Clauses Tests
# ---------------------------------------------------------------------------
class TestRegulationClauses:
    def test_at_least_five_clauses(self):
        assert len(REGULATION_CLAUSES) >= 5

    def test_all_clauses_have_required_fields(self):
        required = ["id", "doc_id", "title", "clause_ref", "clause_text",
                    "valid_from", "valid_to", "keywords"]
        for clause in REGULATION_CLAUSES:
            for field in required:
                assert field in clause, f"Missing field '{field}' in clause {clause.get('id')}"

    def test_valid_from_before_valid_to(self):
        for clause in REGULATION_CLAUSES:
            assert clause["valid_from"] < clause["valid_to"], (
                f"Clause {clause['id']}: valid_from >= valid_to"
            )

    def test_expired_clause_exists(self):
        now = datetime.now(timezone.utc)
        expired = [c for c in REGULATION_CLAUSES if c["valid_to"] < now]
        assert len(expired) >= 1, "There must be at least one expired clause for time-travel testing"

    def test_in_force_clauses_exist(self):
        now = datetime.now(timezone.utc)
        in_force = [c for c in REGULATION_CLAUSES if c["valid_from"] <= now <= c["valid_to"]]
        assert len(in_force) >= 4, "There must be at least 4 in-force clauses"
