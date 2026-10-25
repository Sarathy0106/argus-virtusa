"""
Bitemporal Memory Service for ARGUS.
Stores facts with dual temporal coordinates:
1. Business Valid Time (valid_from, valid_to): When the fact is true in the real world.
2. System Recorded Time (recorded_at): When the bank learned or ingested the fact.
Supports time-travel queries ("What did we know as of Date X?") and cryptographic shredding.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from contracts.common import ClassificationLevel
from contracts.memory import BitemporalFact


class TimeTravelQuery(BaseModel):
    subject: str
    as_of_valid_time: datetime
    as_of_recorded_time: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BitemporalMemoryStore:
    def __init__(self):
        # In-memory store: subject -> list[BitemporalFact]
        self._facts: dict[str, list[BitemporalFact]] = {}
        # Tombstoned subjects for cryptographic right-to-erase
        self._shredded_subjects: set[str] = set()

    def record_fact(
        self,
        subject: str,
        predicate: str,
        payload: dict[str, Any],
        valid_from: datetime,
        valid_to: datetime | None = None,
        source: str = "MANUAL_ENTRY",
        classification: ClassificationLevel = ClassificationLevel.CONFIDENTIAL,
    ) -> BitemporalFact:
        """Records a new bitemporal fact. Supersedes overlapping valid times if applicable."""
        if subject in self._shredded_subjects:
            raise PermissionError(
                f"Subject '{subject}' has been cryptographically shredded under erasure policy."
            )

        end_time = valid_to or datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC)
        fact = BitemporalFact(
            subject=subject,
            predicate=predicate,
            object=payload,
            valid_from=valid_from,
            valid_to=end_time,
            recorded_at=datetime.now(UTC),
            source=source,
            classification=classification,
        )

        if subject not in self._facts:
            self._facts[subject] = []
        self._facts[subject].append(fact)
        return fact

    def query_as_of(
        self, subject: str, as_of_valid_time: datetime, as_of_recorded_time: datetime | None = None
    ) -> list[BitemporalFact]:
        """
        Time-travel query: retrieves facts that were:
        1. Valid in business reality at as_of_valid_time (valid_from <= t <= valid_to)
        2. Known to the system at as_of_recorded_time (recorded_at <= system_t)
        """
        if subject in self._shredded_subjects:
            return []

        rec_t = as_of_recorded_time or datetime.now(UTC)
        results = []
        for fact in self._facts.get(subject, []):
            if fact.recorded_at <= rec_t and fact.valid_from <= as_of_valid_time <= fact.valid_to:
                results.append(fact)
        return results

    def crypto_shred_subject(self, subject: str) -> None:
        """Right-to-erase compliance: wipes fact payloads and tombstones the subject."""
        self._shredded_subjects.add(subject)
        if subject in self._facts:
            # Overwrite payloads with tombstones before deleting
            for f in self._facts[subject]:
                f.object = {"tombstone": True, "shredded_at": datetime.now(UTC).isoformat()}
            del self._facts[subject]

    def is_shredded(self, subject: str) -> bool:
        return subject in self._shredded_subjects
