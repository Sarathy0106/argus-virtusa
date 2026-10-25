"""
KYC and Sanctions Agent for ARGUS Mesh.
Skill: kyc.check_sanctions
Validates entities against sanctions watchlists and checks KYC validity.
"""

from typing import Any

from contracts.agents import AgentCard, AgentSkill
from services.agents.broker import MCPSanctionsTool
from services.agents.crypto import AgentKeyPair


class KYCSanctionsAgent:
    def __init__(
        self, keypair: AgentKeyPair | None = None, sanctions_tool: MCPSanctionsTool | None = None
    ):
        self.keypair = keypair or AgentKeyPair()
        self.sanctions_tool = sanctions_tool or MCPSanctionsTool()

        self.card = AgentCard(
            agent_id="agent.kyc_sanctions",
            name="KYC and Sanctions Verification Agent",
            version="1.0.0",
            public_key=self.keypair.public_key_hex,
            skills=[
                AgentSkill(
                    name="kyc.check_sanctions",
                    description="Performs exact and fuzzy sanctions match against OFAC/UN/RBI watchlists via MCP",
                )
            ],
        )

    def verify_account(self, account_token: str, counterparty_token: str) -> dict[str, Any]:
        origin_check = self.sanctions_tool.search_sanctions(account_token)
        dest_check = self.sanctions_tool.search_sanctions(counterparty_token)

        hit = origin_check["match"] or dest_check["match"]
        matched_target = (
            account_token
            if origin_check["match"]
            else (counterparty_token if dest_check["match"] else None)
        )

        return {
            "account_token": account_token,
            "counterparty_token": counterparty_token,
            "sanctions_hit": hit,
            "matched_entity": matched_target,
            "list_source": origin_check.get("list_source") or dest_check.get("list_source"),
        }
