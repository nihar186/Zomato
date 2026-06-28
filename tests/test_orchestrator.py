import json

from src.api.orchestrator import RecommendationOrchestrator
from src.config import Settings
from src.domain.preferences import Budget, UserPreferences
from src.domain.restaurant import BudgetBand, Restaurant
from src.filtering.pipeline import FilterService
from src.ingestion.indexes import RestaurantIndex
from src.ingestion.service import DataIngestionService
from src.llm.engine import RecommendationEngine
from src.llm.mock_client import MockLLMClient


def _make_ingestion_with_restaurants():
    restaurants = [
        Restaurant(
            id="r1",
            name="Italian Bistro",
            location="Indiranagar",
            city="Bangalore",
            cuisines=["Italian", "Pizza"],
            rating=4.6,
            approximate_cost_for_two=700,
            budget_band=BudgetBand.MEDIUM,
        ),
        Restaurant(
            id="r2",
            name="Chinese Wok",
            location="Koramangala",
            city="Bangalore",
            cuisines=["Chinese"],
            rating=4.3,
            approximate_cost_for_two=500,
            budget_band=BudgetBand.MEDIUM,
        ),
    ]
    ingestion = DataIngestionService(settings=Settings())
    ingestion._restaurants = restaurants
    ingestion._index = RestaurantIndex(
        by_city={"Bangalore": restaurants},
        by_cuisine_token={"italian": [restaurants[0]], "chinese": [restaurants[1]]},
        known_cities=["Bangalore"],
    )
    ingestion._loaded = True
    return ingestion


def test_orchestrator_end_to_end_mock():
    ingestion = _make_ingestion_with_restaurants()
    filter_service = FilterService(settings=Settings(max_candidates=20), known_cities=["Bangalore"])
    mock_response = json.dumps(
        {
            "summary": "Italian options in Bangalore.",
            "recommendations": [
                {
                    "restaurant_id": "r1",
                    "rank": 1,
                    "explanation": "Italian cuisine and high rating in Bangalore.",
                }
            ],
        }
    )
    engine = RecommendationEngine(
        settings=Settings(llm_api_key="test", top_n_results=5),
        llm_client=MockLLMClient(response_text=mock_response),
    )
    orchestrator = RecommendationOrchestrator(ingestion, filter_service, engine)
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
    )
    outcome = orchestrator.recommend(prefs)
    assert len(outcome.response.recommendations) >= 1
    assert outcome.response.recommendations[0].name == "Italian Bistro"
