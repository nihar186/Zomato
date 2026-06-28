"""User preference domain model."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Budget(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UserPreferences(BaseModel):
    location: str
    budget: Budget
    cuisine: Optional[str] = None
    min_rating: float = Field(default=3.0, ge=0.0, le=5.0)
    additional_preferences: Optional[str] = None

    @field_validator("location")
    @classmethod
    def location_not_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Location cannot be empty.")
        return stripped
