"""LLM client interface and factory."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from src.config import Settings, get_settings
from src.llm.messages import ChatMessage, CompletionOptions

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    def complete(
        self,
        messages: List[ChatMessage],
        options: Optional[CompletionOptions] = None,
    ) -> str:
        """Return raw text completion from the model."""


class LLMError(Exception):
    """Base error for LLM provider failures."""


class LLMTimeoutError(LLMError):
    pass


class LLMAuthError(LLMError):
    pass


def create_llm_client(
    settings: Optional[Settings] = None,
    *,
    override_provider: Optional[str] = None,
) -> LLMClient:
    settings = settings or get_settings()
    provider = (override_provider or settings.llm_provider).lower()

    if provider == "mock":
        from src.llm.mock_client import MockLLMClient

        return MockLLMClient()

    if provider == "ollama":
        from src.llm.ollama_client import OllamaClient

        return OllamaClient(settings)

    if provider in ("groq", "openai"):
        from src.llm.groq_client import GroqClient

        return GroqClient(settings)

    logger.warning("Unknown LLM provider '%s'; falling back to Groq client.", provider)
    from src.llm.groq_client import GroqClient

    return GroqClient(settings)
