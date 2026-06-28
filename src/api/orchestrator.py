"""Orchestrates filtering and LLM recommendation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from src.config import Settings, get_settings
from src.domain.preferences import UserPreferences
from src.domain.recommendation import RecommendationMeta, RecommendationResponse
from src.filtering.pipeline import FilterService
from src.filtering.result import FilterResult
from src.ingestion.indexes import RestaurantIndex
from src.ingestion.service import DataIngestionService
from src.llm.engine import RecommendationEngine

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorResult:
    response: RecommendationResponse
    filter_result: FilterResult
    filter_duration_ms: float = 0.0
    llm_duration_ms: float = 0.0


class RecommendationOrchestrator:
    """Single entry point: load data → filter → Groq recommend → format."""

    def __init__(
        self,
        ingestion: DataIngestionService,
        filter_service: FilterService,
        engine: Optional[RecommendationEngine] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._ingestion = ingestion
        self._filter_service = filter_service
        self._settings = settings or get_settings()
        self._engine = engine or RecommendationEngine(self._settings)

    def recommend(self, preferences: UserPreferences) -> OrchestratorResult:
        restaurants = self._ingestion.ensure_loaded()
        index: Optional[RestaurantIndex] = self._ingestion.index

        filter_start = time.perf_counter()
        filter_result = self._filter_service.apply(
            preferences,
            restaurants,
            index=index,
        )
        filter_duration_ms = (time.perf_counter() - filter_start) * 1000

        if filter_result.empty_reason and not filter_result.candidates:
            response = RecommendationResponse(
                summary="No restaurants matched your filters. Try broadening your search.",
                recommendations=[],
                meta=RecommendationMeta(
                    candidates_considered=0,
                    filters_relaxed=filter_result.filters_relaxed,
                    degraded_mode=False,
                ),
            )
            return OrchestratorResult(
                response=response,
                filter_result=filter_result,
                filter_duration_ms=filter_duration_ms,
            )

        llm_start = time.perf_counter()
        response = self._engine.recommend(
            preferences,
            filter_result.candidates,
            candidates_considered=filter_result.candidates_considered,
            filters_relaxed=filter_result.filters_relaxed,
        )
        llm_duration_ms = (time.perf_counter() - llm_start) * 1000

        logger.info(
            "Orchestrator complete: city=%s candidates=%s returned=%s "
            "filter_ms=%.1f llm_ms=%.1f degraded=%s",
            filter_result.resolved_city,
            filter_result.candidates_considered,
            len(response.recommendations),
            filter_duration_ms,
            llm_duration_ms,
            response.meta.degraded_mode,
        )

        return OrchestratorResult(
            response=response,
            filter_result=filter_result,
            filter_duration_ms=filter_duration_ms,
            llm_duration_ms=llm_duration_ms,
        )
