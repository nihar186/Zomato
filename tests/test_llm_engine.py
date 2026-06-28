import json

from src.config import Settings
from src.domain.preferences import Budget, UserPreferences
from src.domain.restaurant import BudgetBand, Restaurant
from src.llm.engine import RecommendationEngine
from src.llm.mock_client import MockLLMClient


def _restaurant(id: str, name: str = "Test") -> Restaurant:
    return Restaurant(
        id=id,
        name=name,
        location="Area",
        city="Bangalore",
        cuisines=["Italian"],
        rating=4.5,
        approximate_cost_for_two=600,
        budget_band=BudgetBand.MEDIUM,
    )


def test_engine_happy_path_with_mock():
    valid = _restaurant("r1", "Italian Place")
    mock_response = json.dumps(
        {
            "summary": "Top Italian restaurants in Bangalore for your medium budget.",
            "recommendations": [
                {
                    "restaurant_id": "r1",
                    "rank": 1,
                    "explanation": "Matches Italian cuisine and 4.0+ rating in Bangalore.",
                }
            ],
        }
    )
    engine = RecommendationEngine(
        settings=Settings(top_n_results=5, llm_provider="mock", llm_api_key="test"),
        llm_client=MockLLMClient(response_text=mock_response),
    )
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
    )
    result = engine.recommend(prefs, [valid], candidates_considered=10)
    assert len(result.recommendations) == 1
    assert result.recommendations[0].name == "Italian Place"
    assert result.recommendations[0].rating == 4.5
    assert result.meta.degraded_mode is False
    assert "Italian" in result.recommendations[0].explanation


def test_engine_drops_hallucinated_ids():
    valid = _restaurant("r1")
    mock_response = json.dumps(
        {
            "summary": "Summary",
            "recommendations": [
                {"restaurant_id": "fake-id", "rank": 1, "explanation": "Bad"},
                {"restaurant_id": "r1", "rank": 2, "explanation": "Good pick for Bangalore."},
            ],
        }
    )
    engine = RecommendationEngine(
        settings=Settings(top_n_results=5, llm_api_key="x"),
        llm_client=MockLLMClient(response_text=mock_response),
    )
    prefs = UserPreferences(location="Bangalore", budget=Budget.MEDIUM)
    result = engine.recommend(prefs, [valid])
    assert len(result.recommendations) == 1
    assert result.recommendations[0].restaurant_id == "r1"


def test_engine_degraded_when_no_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    engine = RecommendationEngine(
        settings=Settings(_env_file=None, llm_provider="openai", llm_api_key="", top_n_results=3),
    )
    prefs = UserPreferences(location="Bangalore", budget=Budget.LOW)
    candidates = [_restaurant("r1"), _restaurant("r2", "Second")]
    result = engine.recommend(prefs, candidates, candidates_considered=5)
    assert result.meta.degraded_mode is True
    assert len(result.recommendations) == 2
    assert "Bangalore" in result.recommendations[0].explanation


def test_engine_degraded_on_invalid_json():
    engine = RecommendationEngine(
        settings=Settings(llm_api_key="x"),
        llm_client=MockLLMClient(response_text="not json at all"),
    )
    prefs = UserPreferences(location="Bangalore", budget=Budget.MEDIUM)
    result = engine.recommend(prefs, [_restaurant("r1")])
    assert result.meta.degraded_mode is True
    assert len(result.recommendations) >= 1


def test_engine_empty_candidates():
    engine = RecommendationEngine(settings=Settings(llm_api_key="x"))
    prefs = UserPreferences(location="Bangalore", budget=Budget.MEDIUM)
    result = engine.recommend(prefs, [])
    assert result.recommendations == []
