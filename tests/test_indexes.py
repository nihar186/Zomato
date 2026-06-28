from src.domain.restaurant import BudgetBand, Restaurant
from src.ingestion.indexes import build_index


def test_build_index_by_city_and_cuisine():
    restaurants = [
        Restaurant(
            id="1",
            name="A",
            location="Indiranagar",
            city="Bangalore",
            cuisines=["Italian", "Pizza"],
            rating=4.5,
            approximate_cost_for_two=600,
            budget_band=BudgetBand.MEDIUM,
        ),
        Restaurant(
            id="2",
            name="B",
            location="Koramangala",
            city="Bangalore",
            cuisines=["Chinese"],
            rating=4.0,
            approximate_cost_for_two=400,
            budget_band=BudgetBand.LOW,
        ),
    ]
    index = build_index(restaurants)
    assert len(index.by_city["Bangalore"]) == 2
    assert len(index.by_city["Indiranagar"]) == 1
    assert len(index.by_city["Koramangala"]) == 1
    assert "italian" in index.by_cuisine_token
    assert "Bangalore" in index.known_cities
    assert "Indiranagar" in index.known_cities
    assert "Koramangala" in index.known_cities

