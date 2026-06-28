"""Mock LLM client for tests and offline development."""

from __future__ import annotations

import json
from typing import List, Optional

from src.llm.messages import ChatMessage, CompletionOptions


class MockLLMClient:
    """Returns a configurable JSON response without calling an external API."""

    def __init__(self, response_text: Optional[str] = None) -> None:
        self._response_text = response_text
        self.last_messages: List[ChatMessage] = []
        self.call_count = 0

    def complete(
        self,
        messages: List[ChatMessage],
        options: Optional[CompletionOptions] = None,
    ) -> str:
        self.call_count += 1
        self.last_messages = list(messages)

        if self._response_text is not None:
            return self._response_text

        # Extract candidate ids from the system prompt for a valid default response.
        system_content = next((m.content for m in messages if m.role == "system"), "")
        ids: List[str] = []
        if "CANDIDATES:" in system_content:
            import re

            block = system_content.split("CANDIDATES:", 1)[1].strip()
            match = re.search(r"(\[[\s\S]*\])", block)
            if match:
                try:
                    candidates = json.loads(match.group(1))
                    ids = [str(item["id"]) for item in candidates if item.get("id")][:5]
                except (json.JSONDecodeError, KeyError, TypeError):
                    ids = []
        if not ids:
            import re

            ids = re.findall(r'"id":\s*"([^"]+)"', system_content)[:5]

        recommendations = []
        for rank, restaurant_id in enumerate(ids[:5], start=1):
            recommendations.append(
                {
                    "restaurant_id": restaurant_id,
                    "rank": rank,
                    "explanation": (
                        f"Rank {rank}: matches your preferences for location, budget, and cuisine."
                    ),
                }
            )

        return json.dumps(
            {
                "summary": "Top picks based on your preferences.",
                "recommendations": recommendations,
            }
        )
