"""
Custom Indian Financial and Identity Recognizers for Microsoft Presidio.
Detects:
1. PAN (Permanent Account Number): 10 characters [A-Z]{5}[0-9]{4}[A-Z]{1}
2. Aadhaar: 12 digits (with optional spaces/hyphens)
3. IFSC (Indian Financial System Code): 11 characters ^[A-Z]{4}0[A-Z0-9]{6}$
4. UPI ID (Virtual Payment Address): e.g. user@okhdfcbank, name@upi
5. Indian Phone Number: +91 or 0 followed by 10 digits starting with 6-9
"""

import re

from pydantic import BaseModel


class PIIEntity(BaseModel):
    entity_type: str  # PAN, AADHAAR, IFSC, UPI, PHONE, EMAIL, ACCOUNT
    start: int
    end: int
    text: str
    confidence: float


# Regex patterns
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
AADHAAR_PATTERN = re.compile(r"\b[2-9]{1}[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b")
IFSC_PATTERN = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
UPI_PATTERN = re.compile(r"\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b")
PHONE_PATTERN = re.compile(r"(?:\+91[\-\s]?|0)?[6-9]\d{4}[\-\s]?\d{5}\b|(?:\+91[\-\s]?|0)?[6-9]\d{9}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


class IndianPIIRecognizer:
    """High-performance Indian identifier extractor without heavy external model download requirements."""

    def analyze(self, text: str) -> list[PIIEntity]:
        entities: list[PIIEntity] = []

        # 1. PAN detection
        for match in PAN_PATTERN.finditer(text):
            entities.append(
                PIIEntity(
                    entity_type="PAN",
                    start=match.start(),
                    end=match.end(),
                    text=match.group(),
                    confidence=0.98,
                )
            )

        # 2. Aadhaar detection
        for match in AADHAAR_PATTERN.finditer(text):
            raw = match.group().replace(" ", "").replace("-", "")
            if len(raw) == 12:
                entities.append(
                    PIIEntity(
                        entity_type="AADHAAR",
                        start=match.start(),
                        end=match.end(),
                        text=match.group(),
                        confidence=0.95,
                    )
                )

        # 3. IFSC detection
        for match in IFSC_PATTERN.finditer(text):
            entities.append(
                PIIEntity(
                    entity_type="IFSC",
                    start=match.start(),
                    end=match.end(),
                    text=match.group(),
                    confidence=0.95,
                )
            )

        # 4. UPI detection (exclude standard email domains like gmail.com if they aren't PSP handles)
        for match in UPI_PATTERN.finditer(text):
            upi_str = match.group()
            # If domain has dot, it's likely an email, unless it's a known UPI handle
            if "." in upi_str.split("@")[1] and not any(
                h in upi_str for h in ["okaxis", "okhdfcbank", "oksbi", "icici", "paytm"]
            ):
                continue
            entities.append(
                PIIEntity(
                    entity_type="UPI",
                    start=match.start(),
                    end=match.end(),
                    text=upi_str,
                    confidence=0.92,
                )
            )

        # 5. Indian Phone Number detection
        for match in PHONE_PATTERN.finditer(text):
            entities.append(
                PIIEntity(
                    entity_type="PHONE",
                    start=match.start(),
                    end=match.end(),
                    text=match.group(),
                    confidence=0.90,
                )
            )

        # 6. Email detection
        for match in EMAIL_PATTERN.finditer(text):
            entities.append(
                PIIEntity(
                    entity_type="EMAIL",
                    start=match.start(),
                    end=match.end(),
                    text=match.group(),
                    confidence=0.95,
                )
            )

        # Sort entities by start position and deduplicate overlapping spans
        entities.sort(key=lambda e: (e.start, -e.end))
        deduped: list[PIIEntity] = []
        last_end = -1
        for e in entities:
            if e.start >= last_end:
                deduped.append(e)
                last_end = e.end

        return deduped
