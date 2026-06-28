"""Restaurant domain model."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class BudgetBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class Restaurant(BaseModel):
    id: str
    name: str
    location: str
    city: str
    cuisines: list[str] = Field(default_factory=list)
    rating: float
    approximate_cost_for_two: Optional[int] = None
    budget_band: BudgetBand = BudgetBand.UNKNOWN
    raw_attributes: dict[str, Any] = Field(default_factory=dict)
