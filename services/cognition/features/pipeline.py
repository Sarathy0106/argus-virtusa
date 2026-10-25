"""
Feature Engineering Pipeline for ARGUS Risk Cognition.
Computes sliding-window velocity aggregations, amount z-ratios,
and NetworkX graph hop distances to flagged counterparties.
"""

from datetime import timedelta
from typing import Any

import networkx as nx

from contracts.transactions import CustomerProfile, Transaction


class FeaturePipeline:
    def __init__(self):
        # Transaction history store: account_token -> list[Transaction]
        self.txn_history: dict[str, list[Transaction]] = {}
        # Device history: device_token -> set[account_token]
        self.device_accounts: dict[str, set[str]] = {}
        # Counterparty interaction graph
        self.graph = nx.Graph()
        # Set of flagged/mule accounts
        self.flagged_accounts: set[str] = set()

    def record_flagged_account(self, account_token: str) -> None:
        self.flagged_accounts.add(account_token)
        self.graph.add_node(account_token, flagged=True)

    def ingest_transaction(self, txn: Transaction) -> None:
        """Indexes transaction into historical sliding window and graph state."""
        # Record account history
        if txn.account_token not in self.txn_history:
            self.txn_history[txn.account_token] = []
        self.txn_history[txn.account_token].append(txn)

        # Record device sharing
        if txn.device_id_token:
            if txn.device_id_token not in self.device_accounts:
                self.device_accounts[txn.device_id_token] = set()
            self.device_accounts[txn.device_id_token].add(txn.account_token)

        # Update counterparty graph
        self.graph.add_edge(
            txn.account_token,
            txn.counterparty_token,
            weight=txn.amount,
            channel=txn.channel.value,
            last_timestamp=txn.timestamp.isoformat(),
        )

    def extract_features(
        self, current_txn: Transaction, profile: CustomerProfile | None = None
    ) -> dict[str, Any]:
        """Computes risk features for a transaction against temporal and graph state."""
        account = current_txn.account_token
        ts = current_txn.timestamp
        history = self.txn_history.get(account, [])

        # Sliding window counts
        one_hour_ago = ts - timedelta(hours=1)
        one_day_ago = ts - timedelta(hours=24)
        seven_days_ago = ts - timedelta(days=7)

        v_1h = sum(1 for t in history if t.timestamp >= one_hour_ago)
        v_24h = sum(1 for t in history if t.timestamp >= one_day_ago)
        v_7d = sum(1 for t in history if t.timestamp >= seven_days_ago)

        # Structuring window (transfers between 45k and 50k in 24h)
        structuring_count = sum(
            1 for t in history if t.timestamp >= one_day_ago and (45000.0 <= t.amount < 50000.0)
        )
        if 45000.0 <= current_txn.amount < 50000.0:
            structuring_count += 1

        # Distinct devices in 24h
        distinct_devices = len(
            {t.device_id_token for t in history if t.timestamp >= one_day_ago and t.device_id_token}
        )
        if current_txn.device_id_token:
            distinct_devices = max(1, distinct_devices)

        # Device sharing (how many OTHER accounts used this same device)
        device_sharing = 0
        if current_txn.device_id_token and current_txn.device_id_token in self.device_accounts:
            other_accs = self.device_accounts[current_txn.device_id_token] - {account}
            device_sharing = len(other_accs)

        # Amount ratio against customer monthly baseline
        avg_vol = profile.average_monthly_volume if profile else 50000.0
        amount_to_avg_ratio = round(current_txn.amount / (avg_vol / 30.0 + 1.0), 3)

        # Graph hop distance to flagged nodes
        graph_hop_dist = 999
        if account in self.graph and self.flagged_accounts:
            for flagged in self.flagged_accounts:
                if flagged in self.graph:
                    try:
                        dist = nx.shortest_path_length(self.graph, source=account, target=flagged)
                        if dist < graph_hop_dist:
                            graph_hop_dist = dist
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        pass

        # Temporal markers
        hour_of_day = ts.hour
        is_weekend = int(ts.weekday() >= 5)

        return {
            "amount": float(current_txn.amount),
            "velocity_count_1h": v_1h,
            "velocity_count_24h": v_24h,
            "velocity_count_7d": v_7d,
            "structuring_window_count_24h": structuring_count,
            "distinct_devices_24h": distinct_devices,
            "shared_device_account_count": device_sharing,
            "amount_to_avg_ratio": amount_to_avg_ratio,
            "graph_hop_distance_to_flagged": graph_hop_dist,
            "hour_of_day": hour_of_day,
            "is_weekend": is_weekend,
            "location_country": current_txn.location_country,
            "sanctions_match": False,
        }
