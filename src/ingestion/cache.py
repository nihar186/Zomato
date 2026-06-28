"""Parquet cache for processed restaurants."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.domain.restaurant import BudgetBand, Restaurant

logger = logging.getLogger(__name__)


def metadata_path(cache_path: Path) -> Path:
    return cache_path.with_name(cache_path.stem + ".meta.json")


def _rows_to_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if "cuisines" in frame.columns:
        frame["cuisines"] = frame["cuisines"].apply(json.dumps)
    if "raw_attributes" in frame.columns:
        frame["raw_attributes"] = frame["raw_attributes"].apply(json.dumps)
    return frame


def _clean_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dataframe_to_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in frame.to_dict(orient="records"):
        cuisines = record.get("cuisines")
        if isinstance(cuisines, str):
            record["cuisines"] = json.loads(cuisines)
        raw = record.get("raw_attributes")
        if isinstance(raw, str):
            record["raw_attributes"] = json.loads(raw)
        record["approximate_cost_for_two"] = _clean_optional_int(
            record.get("approximate_cost_for_two")
        )
        rows.append(record)
    return rows


def save_cache(path: Path, rows: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = _rows_to_dataframe(rows)
    frame.to_parquet(path, index=False)
    metadata_path(path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Wrote cache to %s (%s restaurants)", path, len(rows))


def load_cache(path: Path) -> Optional[list[dict[str, Any]]]:
    if not path.exists():
        return None
    logger.info("Loading cache from %s", path)
    frame = pd.read_parquet(path)
    return _dataframe_to_rows(frame)


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
                approximate_cost_for_two=row.get("approximate_cost_for_two"),
                budget_band=band_value,
                raw_attributes=dict(row.get("raw_attributes") or {}),
            )
        )
    return restaurants
