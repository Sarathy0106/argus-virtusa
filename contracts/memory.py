from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from contracts.common import ClassificationLevel


class BitemporalFact(BaseModel):
    id: int | None = Field(default=None)
    subject: str = Field(..., description="Entity token (e.g. <ACCT_7F3A>)")
    predicate: str = Field(..., description="Attribute name (e.g. risk_category, kyc_status)")
    object: dict[str, Any] = Field(..., description="Fact payload")
    valid_from: datetime = Field(..., description="Business time start")
    valid_to: datetime = Field(
        default_factory=lambda: datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    )
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="System record time"
    )
    source: str = Field(
        ..., description="Origin of fact (e.g. KYC_PORTAL, ANALYST_VERDICT, CORE_BANKING)"
    )
    classification: ClassificationLevel = Field(default=ClassificationLevel.CONFIDENTIAL)

    def is_valid_at(self, target_time: datetime) -> bool:
        """Determines if the fact was business-valid at target_time."""
        return self.valid_from <= target_time <= self.valid_to


class RegulationClause(BaseModel):
    id: str = Field(..., description="Unique clause ID (e.g. RBI-KYC-2016-C23)")
    doc_id: str = Field(..., description="Document identifier")
    title: str = Field(..., description="Section or clause title")
    chapter: str | None = Field(default=None)
    section: str | None = Field(default=None)
    clause_ref: str = Field(..., description="Official reference number")
    clause_text: str = Field(..., description="Exact textual content")
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_to: datetime = Field(
        default_factory=lambda: datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    )
    embedding: list[float] | None = Field(
        default=None, description="Vector embedding for retrieval"
    )

    @property
    def circular_ref(self) -> str:
        return self.doc_id

