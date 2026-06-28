"""Map domain recommendation responses to API schemas."""

from __future__ import annotations

from typing import Optional

from src.api.schemas import (
    RecommendationMetaOut,
    RecommendationOut,
    RecommendationsResponse,
)
from src.domain.recommendation import RecommendationResponse
from src.filtering.result import FilterResult


def to_recommendations_response(
    result: RecommendationResponse,
    *,
    resolved_city: str = "",
    empty_reason: Optional[str] = None,
) -> RecommendationsResponse:
    """Format orchestrator/engine output for POST /api/v1/recommendations."""
    return RecommendationsResponse(
        summary=result.summary,
        recommendations=[
            RecommendationOut(
                rank=item.rank,
                restaurant_id=item.restaurant_id,
                name=item.name,
                cuisine=item.cuisine,
                rating=round(item.rating, 1),
                estimated_cost=item.estimated_cost,
                explanation=item.explanation,
            )
            for item in result.recommendations
        ],
        meta=RecommendationMetaOut(
            candidates_considered=result.meta.candidates_considered,
            filters_relaxed=result.meta.filters_relaxed,
            degraded_mode=result.meta.degraded_mode,
            resolved_city=resolved_city,
            empty_reason=empty_reason,
        ),
    )


def empty_reason_from_filter(filter_result: FilterResult) -> Optional[str]:
    return filter_result.empty_reason
