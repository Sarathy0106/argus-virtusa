"""
ARGUS v2 — Client Service Layer for 10-Stage Circular-to-Rule Console.
Connects Streamlit UI to V2 agents, bank profiles, rule sandbox, and audit ledger.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
UI_ROOT = Path(__file__).resolve().parent.parent

if str(UI_ROOT) in sys.path:
    sys.path.remove(str(UI_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
elif sys.path[0] != str(REPO_ROOT):
    sys.path.remove(str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT))

from datetime import datetime, timezone
import hashlib
from typing import Any

import streamlit as st

from ui.data.seed_v2 import (
    BANK_PROFILES, CIRCULARS, EXISTING_RULES, INTERNAL_POLICIES, SAMPLE_PIPELINE_CASE
)
from services.agents.v2_agents import (
    ApplicabilityVerdict, BacktestAgent, DeploymentAndMonitorAgent, IntakeAgent,
    ObligationAgent, PolicyMapperAgent, RuleAuthorAgent, ValidatorAgent
)


def get_bank_profiles() -> list[dict[str, Any]]:
    return BANK_PROFILES


def get_active_bank_profile() -> dict[str, Any]:
    if "active_bank_profile_id" not in st.session_state:
        st.session_state["active_bank_profile_id"] = BANK_PROFILES[0]["id"]
    active_id = st.session_state["active_bank_profile_id"]
    for p in BANK_PROFILES:
        if p["id"] == active_id:
            return p
    return BANK_PROFILES[0]


def set_active_bank_profile(profile_id: str):
    st.session_state["active_bank_profile_id"] = profile_id


def get_circulars() -> list[dict[str, Any]]:
    return CIRCULARS


get_all_circulars = get_circulars


def get_sample_pipeline() -> dict[str, Any]:
    if "v2_pipeline_case" not in st.session_state:
        st.session_state["v2_pipeline_case"] = dict(SAMPLE_PIPELINE_CASE)
    return st.session_state["v2_pipeline_case"]


get_sample_pipeline_case = get_sample_pipeline


def evaluate_applicability(obligation: dict[str, Any], bank_profile: dict[str, Any]) -> ApplicabilityVerdict:
    agent = ObligationAgent()
    return agent.check_applicability(obligation, bank_profile)


def run_policy_mapping(obligation: dict[str, Any]) -> list[Any]:
    agent = PolicyMapperAgent()
    return agent.map_policies(obligation, INTERNAL_POLICIES, EXISTING_RULES)


def compile_v2_rule(obligation: dict[str, Any], scoped: bool = True) -> Any:
    agent = RuleAuthorAgent()
    scoped_categories = ["CORPORATE", "AD_CAT1_REMITTANCE"] if scoped else []
    return agent.author_rule(obligation, scoped_categories)


def run_v2_backtest(rule: Any, transactions: list[dict[str, Any]]) -> Any:
    agent = BacktestAgent()
    return agent.run_backtest(rule, transactions)


def run_v2_validation(rule: Any, mappings: list[Any], iteration: int = 1) -> Any:
    agent = ValidatorAgent()
    return agent.validate(rule, mappings, iteration)


def simulate_shadow_traffic() -> dict[str, Any]:
    agent = DeploymentAndMonitorAgent()
    return agent.simulate_shadow_run()


def trigger_instant_rollback(rule_id: str, reason: str) -> dict[str, Any]:
    agent = DeploymentAndMonitorAgent()
    return agent.trigger_auto_rollback(rule_id, reason)
