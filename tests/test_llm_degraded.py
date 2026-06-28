from src.domain.preferences import Budget, UserPreferences
from src.domain.restaurant import BudgetBand, Restaurant
from src.llm.degraded import build_degraded_response, format_estimated_cost


def test_format_estimated_cost():
    assert "₹" in format_estimated_cost(800)
    assert format_estimated_cost(None) == "Price not available"


def test_build_degraded_mentions_preferences():
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
    )
    restaurant = Restaurant(
        id="1",
        name="Cafe",
        location="Koramangala",
        city="Bangalore",
        cuisines=["Italian"],
        rating=4.2,
        approximate_cost_for_two=500,
        budget_band=BudgetBand.MEDIUM,
    )
    response = build_degraded_response(prefs, [restaurant], top_n=1, candidates_considered=5)
    assert response.meta.degraded_mode is True
    assert "Bangalore" in response.recommendations[0].explanation
    assert "medium" in response.recommendations[0].explanation
