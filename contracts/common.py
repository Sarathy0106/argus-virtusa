from enum import StrEnum


class DecisionOutcome(StrEnum):
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class RiskTier(StrEnum):
    T0 = "T0"  # Fully automated, sampled QA
    T1 = "T1"  # Analyst review queue with pre-built case
    T2 = "T2"  # Maker-checker (two humans), cannot auto-execute
    T3 = "T3"  # SAR/STR filing, account freeze, compliance officer signoff


class TransactionChannel(StrEnum):
    UPI = "UPI"
    NEFT = "NEFT"
    RTGS = "RTGS"
    IMPS = "IMPS"
    ATM = "ATM"
    POS = "POS"
    WEB = "WEB"


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class ClassificationLevel(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"
