"""Validate normalized restaurant records."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationStats:
    raw_count: int = 0
    valid_count: int = 0
    dropped_missing_name: int = 0
    dropped_missing_location: int = 0
    dropped_missing_city: int = 0
    dropped_missing_rating: int = 0
    dropped_invalid_rating: int = 0

    @property
    def dropped_count(self) -> int:
        return self.raw_count - self.valid_count


def validate_row(row: dict[str, Any], stats: ValidationStats) -> Optional[dict[str, Any]]:
    stats.raw_count += 1

    name = row.get("name") or ""
    location = row.get("location") or ""
    city = row.get("city") or ""
    rating = row.get("rating")

    if not str(name).strip():
        stats.dropped_missing_name += 1
        return None
    if not str(location).strip():
        stats.dropped_missing_location += 1
        return None
    if not str(city).strip():
        stats.dropped_missing_city += 1
        return None
    if rating is None:
        stats.dropped_missing_rating += 1
        return None

    try:
        rating_value = float(rating)
    except (TypeError, ValueError):
        stats.dropped_invalid_rating += 1
        return None

    if not (0.0 <= rating_value <= 5.0):
        stats.dropped_invalid_rating += 1
        return None

    row["rating"] = rating_value
    stats.valid_count += 1
    return row


def validate_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], ValidationStats]:
    stats = ValidationStats()
    valid: list[dict[str, Any]] = []
    for row in rows:
        validated = validate_row(row, stats)
        if validated is not None:
            valid.append(validated)
    logger.info(
        "Validation complete: raw=%s valid=%s dropped=%s",
        stats.raw_count,
        stats.valid_count,
        stats.dropped_count,
    )
    return valid, stats
