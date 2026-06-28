"""Filter service orchestrating the deterministic pipeline."""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from src.config import Settings, get_settings
from src.domain.preferences import UserPreferences
from src.domain.restaurant import Restaurant
from src.filtering.filters import (
    apply_keyword_filter,
    filter_by_budget,
    filter_by_city,
    filter_by_cuisine,
    filter_by_rating,
    sort_candidates,
    truncate,
)
from src.filtering.preferences_validator import PreferenceValidator, ResolvedPreferences
from src.filtering.result import FilterResult
from src.ingestion.indexes import RestaurantIndex

logger = logging.getLogger(__name__)

_RATING_FLOOR = 2.0
_RATING_RELAX_STEP = 0.5


class FilterService:
    """Apply sequential filters and relaxation to produce a candidate shortlist."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        known_cities: Optional[List[str]] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._validator = PreferenceValidator(known_cities=known_cities)

    def apply(
        self,
        preferences: UserPreferences,
        restaurants: List[Restaurant],
        *,
        index: Optional[RestaurantIndex] = None,
        resolved: Optional[ResolvedPreferences] = None,
        skip_relaxation: bool = False,
    ) -> FilterResult:
        start = time.perf_counter()
        resolved_prefs = resolved or self._validator.resolve(preferences)
        city = resolved_prefs.resolved_city

        if index is not None:
            base = index.get_by_city(city)
        else:
            base = filter_by_city(restaurants, city)
        if not base:
            return FilterResult(
                candidates=[],
                candidates_considered=0,
                empty_reason="unknown_location",
                resolved_city=city,
                city_suggestions=resolved_prefs.city_suggestions,
            )

        candidates, relaxation_steps = self._run_pipeline(
            base,
            resolved_prefs.preferences,
            apply_keyword=True,
            budget_relaxed=False,
        )

        if not skip_relaxation and len(candidates) < self._settings.min_candidates:
            candidates, steps = self._relax(
                base,
                resolved_prefs.preferences,
                candidates,
                relaxation_steps,
            )
            relaxation_steps = steps

        considered = len(candidates)
        candidates = truncate(candidates, self._settings.max_candidates)

        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms > 200:
            logger.warning("Filter pipeline took %.1f ms (target < 200 ms)", elapsed_ms)

        empty_reason = None
        if not candidates:
            empty_reason = "no_matches_after_relaxation"

        return FilterResult(
            candidates=candidates,
            candidates_considered=considered,
            filters_relaxed=bool(relaxation_steps),
            relaxation_steps=relaxation_steps,
            empty_reason=empty_reason,
            resolved_city=city,
            city_suggestions=resolved_prefs.city_suggestions,
        )

    def _run_pipeline(
        self,
        base: List[Restaurant],
        preferences: UserPreferences,
        *,
        apply_keyword: bool,
        budget_relaxed: bool,
        min_rating: Optional[float] = None,
        cuisine: Optional[str] = None,
    ) -> tuple[List[Restaurant], List[str]]:
        rating_threshold = min_rating if min_rating is not None else preferences.min_rating
        cuisine_value = cuisine if cuisine is not None else preferences.cuisine

        result = filter_by_rating(base, rating_threshold)
        result = filter_by_cuisine(result, cuisine_value)
        result = filter_by_budget(
            result,
            preferences.budget,
            relaxed=budget_relaxed,
        )
        if apply_keyword:
            result = apply_keyword_filter(result, preferences.additional_preferences)

        result = sort_candidates(result, preferences.budget)
        return result, []

    def _relax(
        self,
        base: List[Restaurant],
        preferences: UserPreferences,
        current: List[Restaurant],
        steps: List[str],
    ) -> tuple[List[Restaurant], List[str]]:
        steps = list(steps)
        candidates = current
        lowered_rating = preferences.min_rating

        def _improved(new: List[Restaurant]) -> bool:
            return len(new) > len(candidates)

        # 1. Widen budget band
        if len(candidates) < self._settings.min_candidates:
            widened, _ = self._run_pipeline(
                base,
                preferences,
                apply_keyword=True,
                budget_relaxed=True,
            )
            if _improved(widened) or (
                len(widened) > 0 and len(candidates) == 0
            ):
                steps.append("budget_widened")
            candidates = widened

        # 2. Drop keyword filter
        if len(candidates) < self._settings.min_candidates:
            without_keyword, _ = self._run_pipeline(
                base,
                preferences,
                apply_keyword=False,
                budget_relaxed=True,
                min_rating=lowered_rating,
            )
            if _improved(without_keyword):
                steps.append("keyword_dropped")
            candidates = without_keyword

        # 3. Lower min_rating
        while (
            len(candidates) < self._settings.min_candidates
            and lowered_rating > _RATING_FLOOR
        ):
            lowered_rating = max(_RATING_FLOOR, lowered_rating - _RATING_RELAX_STEP)
            lowered, _ = self._run_pipeline(
                base,
                preferences,
                apply_keyword=False,
                budget_relaxed=True,
                min_rating=lowered_rating,
            )
            if _improved(lowered):
                steps.append(f"min_rating_lowered_to_{lowered_rating}")
            candidates = lowered

        # 4. Drop cuisine filter
        if len(candidates) < self._settings.min_candidates:
            without_cuisine, _ = self._run_pipeline(
                base,
                preferences,
                apply_keyword=False,
                budget_relaxed=True,
                min_rating=lowered_rating,
                cuisine="",
            )
            if _improved(without_cuisine):
                steps.append("cuisine_dropped")
            candidates = without_cuisine

        return candidates, steps
