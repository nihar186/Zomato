"""Manual QA scenarios for Phase 6A (tasks 6.8–6.9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ManualScenario:
    id: str
    name: str
    description: str
    payload: dict
    endpoint: str = "/api/v1/recommendations"
    expect_status: int = 200
    expect_degraded: Optional[bool] = None
    expect_min_results: int = 0
    expect_filters_relaxed: Optional[bool] = None
    force_degraded: bool = False
    manual_checks: List[str] = field(default_factory=list)


MANUAL_SCENARIOS: List[ManualScenario] = [
    ManualScenario(
        id="QA-01",
        name="Happy path — Italian in Bangalore",
        description="Baseline Groq ranking with medium budget and min rating 4.0.",
        payload={
            "location": "Bangalore",
            "budget": "medium",
            "cuisine": "Italian",
            "min_rating": 4.0,
        },
        expect_min_results=1,
        expect_degraded=False,
        manual_checks=[
            "Each explanation mentions Bangalore, Italian, or medium budget.",
            "Ratings are >= 4.0 and costs feel mid-range.",
        ],
    ),
    ManualScenario(
        id="QA-02",
        name="Low budget Chinese",
        description="Budget band filter with cuisine overlap.",
        payload={
            "location": "Bangalore",
            "budget": "low",
            "cuisine": "Chinese",
            "min_rating": 3.5,
        },
        expect_min_results=1,
        manual_checks=[
            "Estimated costs look affordable for a low budget.",
            "Cuisine tags include Chinese or related Asian options.",
        ],
    ),
    ManualScenario(
        id="QA-03",
        name="High budget North Indian",
        description="Premium picks with higher cost band.",
        payload={
            "location": "Bangalore",
            "budget": "high",
            "cuisine": "North Indian",
            "min_rating": 4.0,
        },
        expect_min_results=1,
        manual_checks=[
            "Costs reflect a high budget (₹600+ for two).",
            "Explanations tie picks to North Indian preference.",
        ],
    ),
    ManualScenario(
        id="QA-04",
        name="Rich preferences with extras",
        description="All preference fields including additional_preferences.",
        payload={
            "location": "Bangalore",
            "budget": "medium",
            "cuisine": "Cafe",
            "min_rating": 4.2,
            "additional_preferences": "family-friendly outdoor seating",
        },
        expect_min_results=1,
        manual_checks=[
            "Summary or explanations reference family-friendly or outdoor seating.",
            "Results still respect Bangalore + medium + Cafe filters.",
        ],
    ),
    ManualScenario(
        id="QA-05",
        name="Strict rating threshold",
        description="High min_rating should surface only top-rated venues.",
        payload={
            "location": "Bangalore",
            "budget": "medium",
            "cuisine": "Pizza",
            "min_rating": 4.5,
        },
        expect_min_results=1,
        manual_checks=[
            "Every recommendation rating is >= 4.5.",
            "Rank order feels sensible (best rating first).",
        ],
    ),
    ManualScenario(
        id="QA-06",
        name="Filter relaxation",
        description="Very narrow filters should widen budget and set filters_relaxed.",
        payload={
            "location": "Bangalore",
            "budget": "low",
            "cuisine": "Lebanese",
            "min_rating": 4.8,
        },
        expect_filters_relaxed=True,
        manual_checks=[
            "meta.filters_relaxed is true when results are sparse.",
            "UI/API shows a relaxed-filter warning if applicable.",
        ],
    ),
    ManualScenario(
        id="QA-07",
        name="Unknown city rejection",
        description="Invalid location should return 400 with suggestions.",
        payload={"location": "Tokyo", "budget": "medium"},
        expect_status=400,
        manual_checks=[
            "Error message is clear and lists city suggestions.",
        ],
    ),
    ManualScenario(
        id="QA-08",
        name="Invalid budget validation",
        description="Schema validation should reject unknown budget values.",
        payload={"location": "Bangalore", "budget": "cheap"},
        expect_status=422,
        manual_checks=[
            "Validation error names the budget field.",
        ],
    ),
    ManualScenario(
        id="QA-09",
        name="Degraded mode without LLM key",
        description="Phase 6.9 — fallback rankings when Groq is unavailable.",
        payload={
            "location": "Bangalore",
            "budget": "medium",
            "cuisine": "Italian",
        },
        force_degraded=True,
        expect_degraded=True,
        expect_min_results=1,
        manual_checks=[
            "meta.degraded_mode is true.",
            "Template explanations still mention user preferences.",
            "Results are ordered by filter score, not Groq rank.",
        ],
    ),
    ManualScenario(
        id="QA-10",
        name="Filter-only candidates endpoint",
        description="Deterministic shortlist without LLM latency.",
        payload={
            "location": "Bangalore",
            "budget": "medium",
            "cuisine": "South Indian",
            "min_rating": 4.0,
        },
        endpoint="/api/v1/candidates",
        expect_min_results=1,
        manual_checks=[
            "Response returns candidate objects with cuisines and budget_band.",
            "No LLM summary or explanation fields are required here.",
        ],
    ),
]
