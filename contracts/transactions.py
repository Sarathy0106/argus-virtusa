from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from contracts.common import TransactionChannel


class Transaction(BaseModel):
    id: str = Field(..., description="Unique transaction ID")
    account_token: str = Field(..., description="Tokenized origin account ID (e.g. <ACCT_7F3A>)")
    counterparty_token: str = Field(..., description="Tokenized destination account ID")
    amount: float = Field(..., gt=0, description="Transaction monetary amount")
    currency: str = Field(default="INR", max_length=3)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    channel: TransactionChannel = Field(default=TransactionChannel.UPI)
    device_id_token: str | None = Field(default=None, description="Tokenized device identifier")
    ip_address_token: str | None = Field(default=None, description="Tokenized IP address")
    location_city: str | None = Field(default=None)
    location_country: str = Field(default="IND", max_length=3)
    narrative: str | None = Field(default=None, description="Payment remarks or user narrative")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_timezone(cls, v: Any) -> datetime:
        if isinstance(v, str):
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v


class CustomerProfile(BaseModel):
    customer_token: str = Field(..., description="Tokenized customer identifier")
    risk_rating: str = Field(default="MEDIUM")  # LOW, MEDIUM, HIGH
    kyc_status: str = Field(default="VALID")  # VALID, PENDING, EXPIRED
    kyc_last_verified: datetime = Field(default_factory=lambda: datetime.now(UTC))
    average_monthly_volume: float = Field(default=50000.0)
    flagged_prior: bool = Field(default=False)
    account_created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
