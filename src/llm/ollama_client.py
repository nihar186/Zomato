"""Ollama local LLM client."""

from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from src.config import Settings
from src.llm.client import LLMClient, LLMError, LLMTimeoutError
from src.llm.messages import ChatMessage, CompletionOptions

logger = logging.getLogger(__name__)


class OllamaClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = (settings.llm_base_url or "http://localhost:11434").rstrip("/")

    def complete(
        self,
        messages: List[ChatMessage],
        options: Optional[CompletionOptions] = None,
    ) -> str:
        options = options or CompletionOptions()
        timeout = (
            options.timeout_seconds
            if options.timeout_seconds is not None
            else self._settings.llm_timeout_seconds
        )
        payload = {
            "model": self._settings.llm_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": options.temperature or self._settings.llm_temperature,
            },
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(f"{self._base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise LLMError(str(exc)) from exc

        content = data.get("message", {}).get("content", "")
        if not content:
            raise LLMError("Empty response from Ollama.")
        return content.strip()
