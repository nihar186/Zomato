"""Groq LLM client (OpenAI-compatible API)."""

from __future__ import annotations

from src.config import Settings
from src.llm.openai_client import OpenAICompatibleClient

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"


def settings_for_groq(settings: Settings) -> Settings:
    """Apply Groq defaults when base URL or model are unset."""
    updates = {}
    if not settings.llm_base_url:
        updates["llm_base_url"] = GROQ_BASE_URL
    if settings.llm_model in ("gpt-4o-mini", "gpt-4o", ""):
        updates["llm_model"] = GROQ_DEFAULT_MODEL
    if updates:
        return settings.model_copy(update=updates)
    return settings


class GroqClient(OpenAICompatibleClient):
    """Chat completions against Groq's OpenAI-compatible endpoint."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings_for_groq(settings))
