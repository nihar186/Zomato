"""Validate and resolve user preferences against dataset metadata."""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import List, Optional

from src.domain.preferences import UserPreferences
from src.ingestion.cities import KNOWN_CITIES, normalize_city


class PreferenceValidationError(ValueError):
    """Raised when preferences cannot be resolved."""

    def __init__(self, message: str, suggestions: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.suggestions = suggestions or []


@dataclass
class ResolvedPreferences:
    preferences: UserPreferences
    resolved_city: str
    city_suggestions: List[str] = field(default_factory=list)


class PreferenceValidator:
    """Resolve location to a canonical city and validate against known cities."""

    def __init__(self, known_cities: Optional[List[str]] = None) -> None:
        self._known_cities = sorted(
            set(known_cities or []) | KNOWN_CITIES,
            key=str.lower,
        )

    def resolve(self, preferences: UserPreferences) -> ResolvedPreferences:
        query = normalize_city(preferences.location)
        if not query:
            raise PreferenceValidationError("Location cannot be empty.")

        exact = self._find_exact(query)
        if exact:
            return ResolvedPreferences(
                preferences=preferences,
                resolved_city=exact,
            )

        suggestions = difflib.get_close_matches(
            query,
            self._known_cities,
            n=5,
            cutoff=0.55,
        )
        if suggestions:
            return ResolvedPreferences(
                preferences=preferences,
                resolved_city=suggestions[0],
                city_suggestions=suggestions,
            )

        if query in KNOWN_CITIES:
            return ResolvedPreferences(preferences=preferences, resolved_city=query)

        raise PreferenceValidationError(
            f"No restaurants found for location '{preferences.location}'.",
            suggestions=suggestions[:5] or list(KNOWN_CITIES)[:5],
        )

    def _find_exact(self, query: str) -> Optional[str]:
        query_lower = query.lower()
        for city in self._known_cities:
            if city.lower() == query_lower:
                return city
        return None
