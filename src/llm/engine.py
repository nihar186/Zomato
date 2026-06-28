"""Recommendation engine: LLM ranking and explanation."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.config import Settings, get_settings
from src.domain.preferences import UserPreferences
from src.domain.recommendation import Recommendation, RecommendationMeta, RecommendationResponse
from src.domain.restaurant import Restaurant
from src.llm.client import LLMClient, LLMError, create_llm_client
from src.llm.degraded import (
    build_degraded_response,
    format_cuisine,
    format_estimated_cost,
)
from src.llm.messages import ChatMessage
from src.llm.parser import LLMOutput, ParseError, parse_llm_output
from src.llm.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class RecommendationEngine:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClient] = None,
        prompt_builder: Optional[PromptBuilder] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm_client
        self._prompt_builder = prompt_builder or PromptBuilder(self._settings)

    def _get_llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = create_llm_client(self._settings)
        return self._llm

    def recommend(
        self,
        preferences: UserPreferences,
        candidates: List[Restaurant],
        *,
        candidates_considered: int = 0,
        filters_relaxed: bool = False,
    ) -> RecommendationResponse:
        if not candidates:
            return RecommendationResponse(
                summary="No restaurants matched your filters.",
                recommendations=[],
                meta=RecommendationMeta(
                    candidates_considered=candidates_considered,
                    filters_relaxed=filters_relaxed,
                    degraded_mode=False,
                ),
            )

        if not self._settings.llm_api_key and self._settings.llm_provider.lower() != "mock":
            logger.warning("LLM API key missing; using degraded mode.")
            return build_degraded_response(
                preferences,
                candidates,
                top_n=self._settings.top_n_results,
                candidates_considered=candidates_considered or len(candidates),
                filters_relaxed=filters_relaxed,
            )

        messages = self._prompt_builder.build(preferences, candidates)
        start = time.perf_counter()
        raw = ""

        try:
            raw = self._get_llm().complete(messages)
            self._maybe_log_exchange(messages, raw)
            parsed = parse_llm_output(raw)
        except LLMError as exc:
            logger.warning("LLM call failed (%s); degraded mode.", exc)
            return build_degraded_response(
                preferences,
                candidates,
                top_n=self._settings.top_n_results,
                candidates_considered=candidates_considered or len(candidates),
                filters_relaxed=filters_relaxed,
            )
        except ParseError as exc:
            logger.warning("Parse failed (%s); retrying once.", exc)
            try:
                raw = self._get_llm().complete(
                    self._prompt_builder.build_fix_json_prompt(raw or str(exc))
                )
                self._maybe_log_exchange(messages, raw)
                parsed = parse_llm_output(raw)
            except Exception as retry_exc:
                logger.warning("Retry failed (%s); degraded mode.", retry_exc)
                return build_degraded_response(
                    preferences,
                    candidates,
                    top_n=self._settings.top_n_results,
                    candidates_considered=candidates_considered or len(candidates),
                    filters_relaxed=filters_relaxed,
                )

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("LLM recommendation completed in %.0f ms", elapsed_ms)

        return self._hydrate_response(
            preferences=preferences,
            candidates=candidates,
            parsed=parsed,
            candidates_considered=candidates_considered or len(candidates),
            filters_relaxed=filters_relaxed,
        )

    def _hydrate_response(
        self,
        preferences: UserPreferences,
        candidates: List[Restaurant],
        parsed: LLMOutput,
        candidates_considered: int,
        filters_relaxed: bool,
    ) -> RecommendationResponse:
        by_id: Dict[str, Restaurant] = {r.id: r for r in candidates}
        recommendations: List[Recommendation] = []
        seen_ids: set = set()

        sorted_items = sorted(parsed.recommendations, key=lambda item: item.rank)
        for item in sorted_items:
            if item.restaurant_id not in by_id:
                logger.warning("Dropping hallucinated restaurant_id=%s", item.restaurant_id)
                continue
            if item.restaurant_id in seen_ids:
                continue
            seen_ids.add(item.restaurant_id)
            restaurant = by_id[item.restaurant_id]
            recommendations.append(
                Recommendation(
                    rank=len(recommendations) + 1,
                    restaurant_id=restaurant.id,
                    name=restaurant.name,
                    cuisine=format_cuisine(restaurant.cuisines),
                    rating=restaurant.rating,
                    estimated_cost=format_estimated_cost(restaurant.approximate_cost_for_two),
                    explanation=item.explanation.strip()
                    or f"Recommended for your preferences in {preferences.location}.",
                )
            )
            if len(recommendations) >= self._settings.top_n_results:
                break

        if not recommendations:
            return build_degraded_response(
                preferences,
                candidates,
                top_n=self._settings.top_n_results,
                candidates_considered=candidates_considered,
                filters_relaxed=filters_relaxed,
            )

        return RecommendationResponse(
            summary=parsed.summary,
            recommendations=recommendations,
            meta=RecommendationMeta(
                candidates_considered=candidates_considered,
                filters_relaxed=filters_relaxed,
                degraded_mode=False,
            ),
        )

    def _maybe_log_exchange(self, messages: List[ChatMessage], raw: str) -> None:
        if not self._settings.llm_log_prompts:
            return
        log_dir = Path(self._settings.llm_log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        file_id = uuid.uuid4().hex[:8]
        path = log_dir / f"{stamp}_{file_id}.json"
        import json

        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "response": raw,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Logged LLM exchange to %s", path)
