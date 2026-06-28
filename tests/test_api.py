"""API integration tests for Phase 4."""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import Settings
from src.domain.restaurant import BudgetBand, Restaurant
from src.ingestion.indexes import RestaurantIndex
from src.ingestion.service import DataIngestionService
from src.llm.mock_client import MockLLMClient


def _bootstrap_services(client: TestClient) -> None:
    """Run lifespan startup with mocked ingestion."""
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
        by_cuisine_token={"italian": [restaurants[0]]},
        known_cities=["Bangalore"],
    )
    ingestion._loaded = True

    import src.api.app as api_module

    api_module._settings = Settings(llm_provider="mock", llm_api_key="test")
    api_module._ingestion = ingestion
    from src.filtering.pipeline import FilterService
    from src.api.orchestrator import RecommendationOrchestrator
    from src.llm.engine import RecommendationEngine
    api_module._filter_service = FilterService(
        settings=api_module._settings,
        known_cities=["Bangalore"],
    )
    mock_response = json.dumps(
        {
            "summary": "Italian picks in Bangalore.",
            "recommendations": [
                {
                    "restaurant_id": "r1",
                    "rank": 1,
                    "explanation": "Italian cuisine in Bangalore with strong rating.",
                }
            ],
        }
    )
    engine = RecommendationEngine(
        api_module._settings,
        llm_client=MockLLMClient(response_text=mock_response),
    )
    api_module._orchestrator = RecommendationOrchestrator(
        ingestion,
        api_module._filter_service,
        engine=engine,
        settings=api_module._settings,
    )
    api_module._ready = True


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        _bootstrap_services(test_client)
        yield test_client


def test_health_ready(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["llm_provider"] == "mock"

    ready = client.get("/health/ready")
    assert ready.status_code == 200


def test_recommendations_happy_path(client: TestClient):
    response = client.post(
        "/api/v1/recommendations",
        json={
            "location": "Bangalore",
            "budget": "medium",
            "cuisine": "Italian",
            "min_rating": 4.0,
        },
    )
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    body = response.json()
    assert body["meta"]["candidates_considered"] >= 1
    assert "filters_relaxed" in body["meta"]
    assert body["meta"]["degraded_mode"] is False
    assert len(body["recommendations"]) >= 1
    rec = body["recommendations"][0]
    assert rec["name"] == "Italian Bistro"
    assert rec["rating"] == 4.6
    assert "₹" in rec["estimated_cost"]
    assert rec["explanation"]


def test_recommendations_degraded_without_key(client: TestClient, monkeypatch):
    import src.api.app as api_module

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    api_module._settings = Settings(_env_file=None, llm_provider="groq", llm_api_key="")
    engine = __import__("src.llm.engine", fromlist=["RecommendationEngine"]).RecommendationEngine(
        api_module._settings
    )
    api_module._orchestrator._engine = engine

    response = client.post(
        "/api/v1/recommendations",
        json={"location": "Bangalore", "budget": "medium", "cuisine": "Italian"},
    )
    assert response.status_code == 200
    assert response.json()["meta"]["degraded_mode"] is True


def test_invalid_budget_returns_422(client: TestClient):
    response = client.post(
        "/api/v1/recommendations",
        json={"location": "Bangalore", "budget": "cheap"},
    )
    assert response.status_code == 422


def test_unknown_city_returns_400(client: TestClient):
    response = client.post(
        "/api/v1/recommendations",
        json={"location": "Tokyo", "budget": "medium"},
    )
    assert response.status_code == 400
    assert "suggestions" in response.json()["detail"]


def test_candidates_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/candidates",
        json={"location": "Bangalore", "budget": "medium", "cuisine": "Italian"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["candidates"]) >= 1
    assert body["meta"]["resolved_city"] == "Bangalore"
