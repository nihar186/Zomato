"""Build LLM prompts for restaurant recommendations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from src.config import Settings, get_settings
from src.domain.preferences import UserPreferences
from src.domain.restaurant import Restaurant
from src.llm.messages import ChatMessage

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "recommendation.txt"


def _serialize_preferences(preferences: UserPreferences) -> dict:
    return {
        "location": preferences.location,
        "budget": preferences.budget.value,
        "cuisine": preferences.cuisine,
        "min_rating": preferences.min_rating,
        "additional_preferences": preferences.additional_preferences,
    }


def _serialize_candidates(candidates: List[Restaurant]) -> List[dict]:
    compact = []
    for restaurant in candidates:
        compact.append(
            {
                "id": restaurant.id,
                "name": restaurant.name,
                "city": restaurant.city,
                "location": restaurant.location,
                "cuisines": restaurant.cuisines[:5],
                "rating": restaurant.rating,
                "approximate_cost_for_two": restaurant.approximate_cost_for_two,
                "budget_band": restaurant.budget_band.value,
            }
        )
    return compact


class PromptBuilder:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._template = _TEMPLATE_PATH.read_text(encoding="utf-8")

    def build(
        self,
        preferences: UserPreferences,
        candidates: List[Restaurant],
    ) -> List[ChatMessage]:
        preferences_json = json.dumps(
            _serialize_preferences(preferences),
            ensure_ascii=False,
        )
        candidates_json = json.dumps(
            _serialize_candidates(candidates),
            ensure_ascii=False,
        )
        system_content = (
            self._template.replace("{{top_n}}", str(self._settings.top_n_results))
            .replace("{{preferences_json}}", preferences_json)
            .replace("{{candidates_json}}", candidates_json)
        )
        return [
            ChatMessage(role="system", content=system_content),
            ChatMessage(
                role="user",
                content=(
                    f"Rank the top {self._settings.top_n_results} restaurants and "
                    "return JSON only."
                ),
            ),
        ]

    def build_fix_json_prompt(self, invalid_output: str) -> List[ChatMessage]:
        return [
            ChatMessage(
                role="system",
                content=(
                    "Fix the following so it is valid JSON matching the schema "
                    '{"summary": str, "recommendations": [{"restaurant_id": str, '
                    '"rank": int, "explanation": str}]}. Return JSON only.'
                ),
            ),
            ChatMessage(role="user", content=invalid_output),
        ]
