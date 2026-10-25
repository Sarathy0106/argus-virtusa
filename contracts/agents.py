from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentSkill(BaseModel):
    name: str = Field(..., description="Skill identifier (e.g. risk.score_transaction)")
    description: str = Field(..., description="Human and machine readable description")
    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for input parameters"
    )
    output_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for return values"
    )
    requires_maker_checker: bool = Field(default=False)


class AgentCard(BaseModel):
    agent_id: str = Field(..., description="Unique agent identifier (e.g. agent.txn_risk)")
    name: str = Field(..., description="Agent display name")
    version: str = Field(default="1.0.0")
    public_key: str = Field(..., description="Ed25519 public key (hex encoded)")
    skills: list[AgentSkill] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=lambda: ["analyst", "compliance_officer"])
    signature: str | None = Field(default=None, description="Signature by master deployment key")


class AgentMessage(BaseModel):
    message_id: str = Field(..., description="UUID for tracking and tracing")
    case_id: str | None = Field(default=None, description="Associated investigation case ID")
    sender_id: str = Field(..., description="Origin agent_id")
    recipient_id: str = Field(..., description="Target agent_id or broker")
    skill: str = Field(..., description="Requested skill name")
    payload: dict[str, Any] = Field(..., description="Parameters (MUST CONTAIN ZERO RAW PII)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    signature: str | None = Field(default=None, description="Ed25519 signature of message payload")
