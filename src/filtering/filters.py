"""Individual filter steps for the restaurant pipeline."""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Set

from src.domain.preferences import Budget, UserPreferences
from src.domain.restaurant import BudgetBand, Restaurant

_BUDGET_BANDS: dict[Budget, Set[BudgetBand]] = {
    Budget.LOW: {BudgetBand.LOW},
    Budget.MEDIUM: {BudgetBand.MEDIUM},
    Budget.HIGH: {BudgetBand.HIGH},
}


def expanded_budget_bands(budget: Budget) -> Set[BudgetBand]:
    """One-step wider bands for relaxation (FIL-07)."""
    if budget == Budget.LOW:
        return {BudgetBand.LOW, BudgetBand.MEDIUM}
    if budget == Budget.MEDIUM:
        return {BudgetBand.LOW, BudgetBand.MEDIUM, BudgetBand.HIGH}
    return {BudgetBand.MEDIUM, BudgetBand.HIGH}


def filter_by_city(restaurants: Iterable[Restaurant], city: str) -> List[Restaurant]:
    city_lower = city.strip().lower()
    return [
        r
        for r in restaurants
        if r.city.strip().lower() == city_lower or r.location.strip().lower() == city_lower
    ]



def filter_by_rating(restaurants: Iterable[Restaurant], min_rating: float) -> List[Restaurant]:
    return [r for r in restaurants if r.rating >= min_rating]


def parse_cuisine_tokens(cuisine: Optional[str]) -> List[str]:
    if not cuisine or not cuisine.strip():
        return []
    return [token.strip().lower() for token in re.split(r"[,|/]+", cuisine) if token.strip()]


def filter_by_cuisine(restaurants: Iterable[Restaurant], cuisine: Optional[str]) -> List[Restaurant]:
    tokens = parse_cuisine_tokens(cuisine)
    if not tokens:
        return list(restaurants)
    matched: List[Restaurant] = []
    for restaurant in restaurants:
        haystack = " ".join(restaurant.cuisines).lower()
        if any(token in haystack for token in tokens):
            matched.append(restaurant)
    return matched


def filter_by_budget(
    restaurants: Iterable[Restaurant],
    budget: Budget,
    *,
    relaxed: bool = False,
) -> List[Restaurant]:
    allowed = expanded_budget_bands(budget) if relaxed else _BUDGET_BANDS[budget]
    return [r for r in restaurants if r.budget_band in allowed]


def parse_keywords(additional: Optional[str]) -> List[str]:
    if not additional or not additional.strip():
        return []
    return [
        word.strip().lower()
        for word in re.split(r"[,;]+|\s+and\s+", additional.lower())
        if word.strip()
    ]


def _restaurant_search_text(restaurant: Restaurant) -> str:
    parts = [restaurant.name, restaurant.location, " ".join(restaurant.cuisines)]
    return " ".join(parts).lower()


def apply_keyword_filter(
    restaurants: List[Restaurant],
    additional_preferences: Optional[str],
) -> List[Restaurant]:
    """
  Soft keyword filter (FIL-09): narrow to matches when any exist;
  otherwise return the input list unchanged.
    """
    keywords = parse_keywords(additional_preferences)
    if not keywords:
        return restaurants

    matched = [
        r
        for r in restaurants
        if any(keyword in _restaurant_search_text(r) for keyword in keywords)
    ]
    return matched if matched else restaurants


def sort_candidates(restaurants: List[Restaurant], budget: Budget) -> List[Restaurant]:
    """Rating desc, then cost fit for budget band, then stable id."""

    def cost_key(restaurant: Restaurant) -> tuple:
        cost = restaurant.approximate_cost_for_two
        if cost is None:
            return (1, 0)
        if budget == Budget.LOW:
            return (0, cost)
        if budget == Budget.HIGH:
            return (0, -cost)
        return (0, abs(cost - 600))

    return sorted(
        restaurants,
        key=lambda r: (-r.rating, cost_key(r), r.id),
    )


def truncate(restaurants: List[Restaurant], max_candidates: int) -> List[Restaurant]:
    return restaurants[:max_candidates]
