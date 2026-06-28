"""Map raw Hugging Face rows to partial restaurant dicts."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Optional

from src.ingestion.cities import extract_city_from_address, normalize_city

_RATE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*/\s*5", re.IGNORECASE)
_COST_RANGE_PATTERN = re.compile(r"(\d+)\s*[-–]\s*(\d+)")


def parse_rating(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.upper() == "NEW" or text == "-":
        return None
    match = _RATE_PATTERN.search(text)
    if match:
        value = float(match.group(1))
        if 0.0 <= value <= 5.0:
            return value
    try:
        value = float(text)
        if 0.0 <= value <= 5.0:
            return value
    except ValueError:
        return None
    return None


def parse_cost(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    text = str(raw).strip().replace(",", "").replace("₹", "")
    if not text or text.lower() in {"none", "nan", "-"}:
        return None
    range_match = _COST_RANGE_PATTERN.search(text)
    if range_match:
        low = int(range_match.group(1))
        high = int(range_match.group(2))
        return (low + high) // 2
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return None
    value = int(digits)
    return value if value > 0 else None


def parse_cuisines(raw: Any) -> list[str]:
    if raw is None:
        return []
    text = str(raw).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def make_restaurant_id(name: str, city: str, location: str, row_index: int) -> str:
    payload = f"{name}|{city}|{location}|{row_index}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def normalize_row(row: dict[str, Any], row_index: int) -> dict[str, Any]:
    """Convert a raw HF row into a dict ready for validation and enrichment."""
    name = str(row.get("name") or "").strip()
    location = str(row.get("location") or row.get("listed_in(city)") or "").strip()
    city = extract_city_from_address(row.get("address"))
    if not city:
        city = normalize_city(str(row.get("listed_in(city)") or ""))

    return {
        "id": make_restaurant_id(name, city, location, row_index),
        "name": name,
        "location": location,
        "city": city,
        "cuisines": parse_cuisines(row.get("cuisines")),
        "rating": parse_rating(row.get("rate")),
        "approximate_cost_for_two": parse_cost(row.get("approx_cost(for two people)")),
        "raw_attributes": {
            key: value
            for key, value in row.items()
            if key
            not in {
                "name",
                "location",
                "listed_in(city)",
                "address",
                "cuisines",
                "rate",
                "approx_cost(for two people)",
            }
        },
    }
