"""LLM chat message types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Role = Literal["system", "user", "assistant"]


@dataclass
class ChatMessage:
    role: Role
    content: str


@dataclass
class CompletionOptions:
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout_seconds: Optional[float] = None
