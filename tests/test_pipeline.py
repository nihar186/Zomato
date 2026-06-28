from src.config import Settings
from src.domain.preferences import Budget, UserPreferences
from src.domain.restaurant import BudgetBand, Restaurant
from src.filtering.pipeline import FilterService


def _restaurant(**kwargs) -> Restaurant:
    defaults = dict(
        id="1",
        name="Trattoria",
        location="Indiranagar",
        city="Bangalore",
        cuisines=["Italian", "Pizza"],
        rating=4.5,
        approximate_cost_for_two=800,
        budget_band=BudgetBand.MEDIUM,
    )
    defaults.update(kwargs)
    return Restaurant(**defaults)


def _sample_pool() -> list[Restaurant]:
    return [
        _restaurant(id="1", name="Italian High", rating=4.6, budget_band=BudgetBand.MEDIUM),
        _restaurant(
            id="2",
            name="Italian Low",
            rating=4.2,
            budget_band=BudgetBand.LOW,
            approximate_cost_for_two=300,
        ),
        _restaurant(
            id="3",
            name="Chinese Place",
            cuisines=["Chinese"],
            rating=4.4,
            budget_band=BudgetBand.MEDIUM,
        ),
        _restaurant(
            id="4",
            name="Budget Italian",
            rating=3.2,
            budget_band=BudgetBand.LOW,
            cuisines=["Italian"],
        ),
    ]


def test_pipeline_bangalore_italian_medium():
    settings = Settings(max_candidates=20, min_candidates=3)
    service = FilterService(settings=settings, known_cities=["Bangalore"])
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
    )
    result = service.apply(prefs, _sample_pool(), skip_relaxation=True)
    assert len(result.candidates) >= 1
    assert all("Italian" in " ".join(c.cuisines) for c in result.candidates)
    assert all(c.rating >= 4.0 for c in result.candidates)


def test_pipeline_respects_max_candidates():
    pool = [
        _restaurant(id=str(i), rating=4.0 + i * 0.01, cuisines=["Italian"])
        for i in range(30)
    ]
    settings = Settings(max_candidates=5, min_candidates=3)
    service = FilterService(settings=settings, known_cities=["Bangalore"])
    prefs = UserPreferences(location="Bangalore", budget=Budget.MEDIUM, cuisine="Italian")
    result = service.apply(prefs, pool, skip_relaxation=True)
    assert len(result.candidates) <= 5


def test_relaxation_widens_budget_when_few_results():
    pool = [
        _restaurant(
            id="1",
            name="Only Low",
            cuisines=["Italian"],
            rating=4.5,
            budget_band=BudgetBand.LOW,
        ),
    ]
    settings = Settings(max_candidates=20, min_candidates=3)
    service = FilterService(settings=settings, known_cities=["Bangalore"])
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
    )
    result = service.apply(prefs, pool)
    assert result.filters_relaxed is True
    assert "budget_widened" in result.relaxation_steps
    assert len(result.candidates) >= 1


def test_relaxation_lowers_rating_when_needed():
    pool = [
        _restaurant(id="1", rating=3.3, cuisines=["Italian"], budget_band=BudgetBand.MEDIUM),
        _restaurant(id="2", rating=3.4, cuisines=["Italian"], budget_band=BudgetBand.MEDIUM),
        _restaurant(id="3", rating=3.5, cuisines=["Italian"], budget_band=BudgetBand.MEDIUM),
    ]
    settings = Settings(max_candidates=20, min_candidates=3)
    service = FilterService(settings=settings, known_cities=["Bangalore"])
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=4.5,
    )
    result = service.apply(prefs, pool)
    assert result.filters_relaxed is True
    assert any("min_rating_lowered" in step for step in result.relaxation_steps)
    assert len(result.candidates) >= 3


def test_empty_city_returns_empty_reason():
    settings = Settings()
    service = FilterService(settings=settings, known_cities=["Bangalore"])
    prefs = UserPreferences(location="Bangalore", budget=Budget.LOW)
    result = service.apply(
        prefs,
        [_restaurant(city="Delhi")],
        skip_relaxation=True,
    )
    assert result.candidates == []
    assert result.empty_reason == "unknown_location"
