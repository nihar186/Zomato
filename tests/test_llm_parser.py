import json

import pytest

from src.llm.parser import LLMOutput, ParseError, parse_llm_output, strip_markdown_fences


def test_parse_valid_json():
    raw = json.dumps(
        {
            "summary": "Great Italian picks.",
            "recommendations": [
                {
                    "restaurant_id": "abc",
                    "rank": 1,
                    "explanation": "Best Italian in Bangalore.",
                }
            ],
        }
    )
    result = parse_llm_output(raw)
    assert isinstance(result, LLMOutput)
    assert result.summary == "Great Italian picks."
    assert result.recommendations[0].restaurant_id == "abc"


def test_parse_fenced_json():
    raw = """```json
{"summary": "Hi", "recommendations": [{"restaurant_id": "x", "rank": 1, "explanation": "ok"}]}
```"""
    assert strip_markdown_fences(raw).startswith("{")
    result = parse_llm_output(raw)
    assert result.recommendations[0].restaurant_id == "x"


def test_parse_malformed_json_raises():
    with pytest.raises(ParseError):
        parse_llm_output("{ not valid json")


def test_parse_invalid_item_raises():
    with pytest.raises(ParseError):
        parse_llm_output('{"recommendations": [{"rank": 1, "explanation": "x"}]}')
