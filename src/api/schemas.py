"""API request/response schemas."""

from __future__ import annotations

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from src.domain.preferences import Budget


class RecommendationRequest(BaseModel):
    location: str = Field(..., max_length=50)
    budget: Budget
    cuisine: Optional[str] = Field(default=None, max_length=100)
    min_rating: float = Field(default=3.0, ge=0.0, le=5.0)
    additional_preferences: Optional[str] = Field(default=None, max_length=500)

    @field_validator("location", "cuisine", "additional_preferences", mode="before")
    @classmethod
    def sanitize_strings(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            # Strip HTML tags
            v = re.sub(r"<[^>]*>", "", v)
            # Remove excessive whitespace
            v = " ".join(v.split())
        return v


class CandidateOut(BaseModel):
    id: str
    name: str
    city: str
    location: str
    cuisines: List[str]
    rating: float
    approximate_cost_for_two: Optional[int] = None
    budget_band: str


class FilterMetaOut(BaseModel):
    candidates_considered: int
    filters_relaxed: bool
    relaxation_steps: List[str] = Field(default_factory=list)
    empty_reason: Optional[str] = None
    resolved_city: str = ""
    city_suggestions: List[str] = Field(default_factory=list)


class CandidatesResponse(BaseModel):
    candidates: List[CandidateOut]
    meta: FilterMetaOut


class RecommendationOut(BaseModel):
    rank: int
    restaurant_id: str
    name: str
    cuisine: str
    rating: float
    estimated_cost: str
    explanation: str


class RecommendationMetaOut(BaseModel):
    candidates_considered: int = 0
    filters_relaxed: bool = False
    degraded_mode: bool = False
    resolved_city: str = ""
    empty_reason: Optional[str] = None


class RecommendationsResponse(BaseModel):
    summary: Optional[str] = None
    recommendations: List[RecommendationOut] = Field(default_factory=list)
    meta: RecommendationMetaOut = Field(default_factory=RecommendationMetaOut)
