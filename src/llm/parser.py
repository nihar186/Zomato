"""Parse and validate LLM JSON responses."""

from __future__ import annotations

import json
import re
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError

_JSON_FENCE_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class LLMRecommendationItem(BaseModel):
    restaurant_id: str
    rank: int
    explanation: str


class LLMOutput(BaseModel):
    summary: Optional[str] = None
    recommendations: List[LLMRecommendationItem] = Field(default_factory=list)


class ParseError(ValueError):
    pass


def strip_markdown_fences(text: str) -> str:
    match = _JSON_FENCE_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def parse_llm_output(raw: str) -> LLMOutput:
    cleaned = strip_markdown_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON: {exc}") from exc
    try:
        return LLMOutput.model_validate(data)
    except ValidationError as exc:
        raise ParseError(f"Schema validation failed: {exc}") from exc
