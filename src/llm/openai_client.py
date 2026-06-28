"""OpenAI-compatible chat completion client."""

from __future__ import annotations

import logging
from typing import List, Optional

from openai import APIConnectionError, APITimeoutError, AuthenticationError, OpenAI

from src.config import Settings
from src.llm.client import LLMAuthError, LLMClient, LLMError, LLMTimeoutError
from src.llm.messages import ChatMessage, CompletionOptions

logger = logging.getLogger(__name__)


class OpenAICompatibleClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        kwargs = {"api_key": settings.llm_api_key or "not-set"}
        if settings.llm_base_url:
            kwargs["base_url"] = settings.llm_base_url
        self._client = OpenAI(**kwargs)

    def complete(
        self,
        messages: List[ChatMessage],
        options: Optional[CompletionOptions] = None,
    ) -> str:
        options = options or CompletionOptions()
        temperature = (
            options.temperature
            if options.temperature is not None
            else self._settings.llm_temperature
        )
        max_tokens = (
            options.max_tokens
            if options.max_tokens is not None
            else self._settings.llm_max_tokens
        )
        timeout = (
            options.timeout_seconds
            if options.timeout_seconds is not None
            else self._settings.llm_timeout_seconds
        )

        try:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        except AuthenticationError as exc:
            raise LLMAuthError(str(exc)) from exc
        except APITimeoutError as exc:
            raise LLMTimeoutError(str(exc)) from exc
        except APIConnectionError as exc:
            raise LLMError(str(exc)) from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMError("Empty response from LLM.")
        return content.strip()
