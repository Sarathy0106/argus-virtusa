"""
Bank Profile and Institution Classification Contracts for ARGUS v2.
Used by the Applicability Engine to filter regulatory circulars against
institution type, licenses, active products, channels, and jurisdiction.
"""

from enum import Enum
from pydantic import BaseModel, Field


class BankType(str, Enum):
    SCHEDULED_COMMERCIAL_BANK = "SCHEDULED_COMMERCIAL_BANK"
    SMALL_FINANCE_BANK = "SMALL_FINANCE_BANK"
    PAYMENTS_BANK = "PAYMENTS_BANK"
    REGIONAL_RURAL_BANK = "REGIONAL_RURAL_BANK"
    NBFC = "NBFC"
    COOPERATIVE_BANK = "COOPERATIVE_BANK"


class ProductType(str, Enum):
    UPI = "UPI"
    IMPS = "IMPS"
    RTGS = "RTGS"
    NEFT = "NEFT"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    FOREX_REMITTANCE = "FOREX_REMITTANCE"
    CORPORATE_LOANS = "CORPORATE_LOANS"
    RETAIL_DEPOSITS = "RETAIL_DEPOSITS"


class BankProfile(BaseModel):
    bank_id: str = Field(..., description="Unique bank code (e.g., APEX_IN_001)")
    bank_name: str = Field(..., description="Full legal name of the bank")
    bank_type: BankType = Field(default=BankType.SCHEDULED_COMMERCIAL_BANK)
    licenses: list[str] = Field(
        default_factory=lambda: ["RETAIL_BANKING", "COMMERCIAL_BANKING", "PAYMENT_SYSTEM_OPERATOR", "FOREX_AD_CAT1"],
        description="Regulatory licenses held by the bank",
    )
    active_products: list[ProductType] = Field(
        default_factory=lambda: [
            ProductType.UPI,
            ProductType.IMPS,
            ProductType.RTGS,
            ProductType.NEFT,
            ProductType.CREDIT_CARD,
            ProductType.DEBIT_CARD,
        ]
    )
    supported_channels: list[str] = Field(
        default_factory=lambda: ["UPI", "MOBILE", "NET_BANKING", "ATM", "BRANCH"]
    )
    jurisdictions: list[str] = Field(default_factory=lambda: ["IN"])
    base_currency: str = Field(default="INR")
    risk_tier: str = Field(default="SYSTEMICALLY_IMPORTANT")
