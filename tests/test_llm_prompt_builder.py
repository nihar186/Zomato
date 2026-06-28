from src.config import Settings
from src.domain.preferences import Budget, UserPreferences
from src.domain.restaurant import BudgetBand, Restaurant
from src.llm.prompt_builder import PromptBuilder


def test_prompt_builder_includes_preferences_and_candidates():
    builder = PromptBuilder(settings=Settings(top_n_results=5))
    prefs = UserPreferences(location="Bangalore", budget=Budget.MEDIUM, cuisine="Italian")
    candidates = [
        Restaurant(
            id="r1",
            name="Trattoria",
            location="Indiranagar",
            city="Bangalore",
            cuisines=["Italian"],
            rating=4.5,
            approximate_cost_for_two=800,
            budget_band=BudgetBand.MEDIUM,
        )
    ]
    messages = builder.build(prefs, candidates)
    assert len(messages) == 2
    assert "Bangalore" in messages[0].content
    assert '"id": "r1"' in messages[0].content or '"id":"r1"' in messages[0].content.replace(" ", "")
