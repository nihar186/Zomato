"""JSON cache for processed restaurants."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Optional

from src.domain.restaurant import BudgetBand, Restaurant

logger = logging.getLogger(__name__)


def metadata_path(cache_path: Path) -> Path:
    return cache_path.with_name(cache_path.stem + ".meta.json")


def _clean_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    # Check for float nan/inf
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def save_cache(
    path: Path,
    rows: list[dict[str, Any]],
    metadata: dict[str, Any],
    *,
    include_raw_attributes: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    
    clean_rows = []
    for row in rows:
        clean_row = {
            "id": row.get("id"),
            "name": row.get("name"),
            "location": row.get("location"),
            "city": row.get("city"),
            "cuisines": row.get("cuisines"),
            "rating": row.get("rating"),
            "approximate_cost_for_two": _clean_optional_int(row.get("approximate_cost_for_two")),
            "budget_band": row.get("budget_band"),
        }
        if include_raw_attributes and "raw_attributes" in row:
            clean_row["raw_attributes"] = row["raw_attributes"]
        clean_rows.append(clean_row)
        
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean_rows, f, indent=2)
        
    metadata_path(path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Wrote cache to %s (%s restaurants)", path, len(rows))


def load_cache(path: Path, *, include_raw_attributes: bool = False) -> Optional[list[dict[str, Any]]]:
    if not path.exists():
        return None
    logger.info("Loading cache from %s", path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = json.load(f)
        
        if not include_raw_attributes:
            for row in rows:
                row.pop("raw_attributes", None)
        return rows
    except Exception as e:
        logger.error("Failed to load cache: %s", e)
        return None


def cache_exists(path: Path) -> bool:
    return path.exists()


def dicts_to_restaurants(rows: list[dict[str, Any]]) -> list[Restaurant]:
    restaurants: list[Restaurant] = []
    for row in rows:
        band = row.get("budget_band", BudgetBand.UNKNOWN.value)
        if isinstance(band, BudgetBand):
            band_value = band
        else:
            band_value = BudgetBand(str(band))
        restaurants.append(
            Restaurant(
                id=str(row["id"]),
                name=str(row["name"]),
                location=str(row["location"]),
                city=str(row["city"]),
                cuisines=list(row.get("cuisines") or []),
                rating=float(row["rating"]),
                approximate_cost_for_two=_clean_optional_int(row.get("approximate_cost_for_two")),
                budget_band=band_value,
                raw_attributes=dict(row.get("raw_attributes") or {}),
            )
        )
    return restaurants
