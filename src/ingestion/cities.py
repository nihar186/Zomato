"""City extraction helpers and quality filters."""

from __future__ import annotations

import re
from typing import Optional

from src.config import CITY_ALIASES

_INVALID_CITY_PATTERN = re.compile(
    r"\d|road|street|stage|block|feet|main|colony|land\s*mark|delivery\s*only|cross",
    re.IGNORECASE,
)

KNOWN_CITIES = {
    "Bangalore",
    "Delhi",
    "Mumbai",
    "Kolkata",
    "Chennai",
    "Hyderabad",
    "Pune",
    "Ahmedabad",
    "Gurgaon",
    "Noida",
    "Ghaziabad",
    "Jaipur",
    "Lucknow",
    "Chandigarh",
    "Goa",
    "Indore",
    "Bhopal",
    "Kochi",
    "Coimbatore",
    "Mysore",
    "Mysuru",
    "Vadodara",
    "Surat",
    "Nagpur",
    "Visakhapatnam",
    "Patna",
    "Ludhiana",
    "Amritsar",
    "Guwahati",
    "Bhubaneswar",
    "Trivandrum",
    "Thiruvananthapuram",
}


def normalize_city(raw_city: str) -> str:
    """Apply alias map and title-case unknown cities."""
    stripped = raw_city.strip()
    if not stripped:
        return ""
    alias = CITY_ALIASES.get(stripped.lower())
    if alias:
        return alias
    return stripped.title()


def _is_known_city(city: str) -> bool:
    return city in KNOWN_CITIES


def extract_city_from_address(address: Optional[str]) -> str:
    """Find a known city token in the address (prefer rightmost match)."""
    if not address or not str(address).strip():
        return ""
    parts = [part.strip() for part in str(address).split(",") if part.strip()]
    if not parts:
        return ""

    for part in reversed(parts):
        normalized = normalize_city(part)
        if _is_known_city(normalized):
            return normalized

    # Last segment if it normalizes to a known alias target.
    last = normalize_city(parts[-1])
    if _is_known_city(last):
        return last

    # Substring match for combined tokens like "BTM Bangalore"
    combined = normalize_city(" ".join(parts[-2:])) if len(parts) >= 2 else last
    for city in KNOWN_CITIES:
        if city.lower() in combined.lower():
            return city

    return ""

