"""Degraded-mode recommendations when the LLM is unavailable."""

from __future__ import annotations

from typing import List, Optional

from src.domain.preferences import UserPreferences
from src.domain.recommendation import Recommendation, RecommendationMeta, RecommendationResponse
from src.domain.restaurant import Restaurant


def format_estimated_cost(cost: Optional[int]) -> str:
    if cost is None:
        return "Price not available"
    return f"₹{cost:,} for two"


def format_cuisine(cuisines: List[str]) -> str:
    return ", ".join(cuisines) if cuisines else "Not specified"


def template_explanation(preferences: UserPreferences, restaurant: Restaurant) -> str:
    parts = [
        f"Rated {restaurant.rating:.1f} in {preferences.location}",
        f"fits your {preferences.budget.value} budget",
    ]
    if preferences.cuisine:
        parts.append(f"and serves {preferences.cuisine} cuisine")
    if preferences.min_rating:
        parts.append(f"(min rating {preferences.min_rating})")
    return ". ".join(parts) + "."


def build_degraded_response(
    preferences: UserPreferences,
    candidates: List[Restaurant],
    *,
    top_n: int,
    candidates_considered: int,
    filters_relaxed: bool = False,
) -> RecommendationResponse:
    selected = candidates[:top_n]
    recommendations = [
        Recommendation(
            rank=index,
            restaurant_id=restaurant.id,
            name=restaurant.name,
            cuisine=format_cuisine(restaurant.cuisines),
            rating=restaurant.rating,
            estimated_cost=format_estimated_cost(restaurant.approximate_cost_for_two),
            explanation=template_explanation(preferences, restaurant),
        )
        for index, restaurant in enumerate(selected, start=1)
    ]
    return RecommendationResponse(
        summary=(
            f"Top {len(recommendations)} restaurants in {preferences.location} "
            f"matching your {preferences.budget.value} budget (basic ranking mode)."
        ),
        recommendations=recommendations,
        meta=RecommendationMeta(
            candidates_considered=candidates_considered,
            filters_relaxed=filters_relaxed,
            degraded_mode=True,
        ),
    )
