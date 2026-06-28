"""Filter pipeline result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from src.domain.restaurant import Restaurant


@dataclass
class FilterResult:
    candidates: List[Restaurant]
    candidates_considered: int
    filters_relaxed: bool = False
    relaxation_steps: List[str] = field(default_factory=list)
    empty_reason: Optional[str] = None
    resolved_city: str = ""
    city_suggestions: List[str] = field(default_factory=list)
