"""Recommendation response domain models."""

from typing import Optional

from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    rank: int
    restaurant_id: str
    name: str
    cuisine: str
    rating: float
    estimated_cost: str
    explanation: str


class RecommendationMeta(BaseModel):
    candidates_considered: int = 0
    filters_relaxed: bool = False
    degraded_mode: bool = False


class RecommendationResponse(BaseModel):
    summary: Optional[str] = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    meta: RecommendationMeta = Field(default_factory=RecommendationMeta)
