from src.domain.preferences import Budget
from src.domain.restaurant import BudgetBand, Restaurant
from src.filtering.filters import (
    apply_keyword_filter,
    expanded_budget_bands,
    filter_by_budget,
    filter_by_city,
    filter_by_cuisine,
    filter_by_rating,
    parse_cuisine_tokens,
    sort_candidates,
    truncate,
)


def _restaurant(
    *,
    id: str = "1",
    name: str = "Test",
    city: str = "Bangalore",
    cuisines: list = None,
    rating: float = 4.0,
    cost: int = 500,
    band: BudgetBand = BudgetBand.MEDIUM,
) -> Restaurant:
    return Restaurant(
        id=id,
        name=name,
        location="Area",
        city=city,
        cuisines=cuisines or ["Italian"],
        rating=rating,
        approximate_cost_for_two=cost,
        budget_band=band,
    )


def test_filter_by_city_case_insensitive():
    r1 = Restaurant(
        id="1",
        name="Jalsa",
        location="Banashankari",
        city="Bangalore",
        cuisines=["Indian"],
        rating=4.0,
        approximate_cost_for_two=800,
        budget_band=BudgetBand.MEDIUM,
    )
    r2 = Restaurant(
        id="2",
        name="Taco Bell",
        location="Indiranagar",
        city="Bangalore",
        cuisines=["Mexican"],
        rating=4.2,
        approximate_cost_for_two=500,
        budget_band=BudgetBand.MEDIUM,
    )
    rows = [r1, r2]
    assert len(filter_by_city(rows, "bangalore")) == 2
    assert len(filter_by_city(rows, "indiranagar")) == 1
    assert filter_by_city(rows, "indiranagar")[0].id == "2"



def test_filter_by_rating():
    rows = [_restaurant(rating=4.5), _restaurant(id="2", rating=3.0)]
    assert len(filter_by_rating(rows, 4.0)) == 1


def test_filter_by_cuisine_or_semantics():
    rows = [
        _restaurant(cuisines=["Italian"]),
        _restaurant(id="2", cuisines=["Chinese"]),
    ]
    assert len(filter_by_cuisine(rows, "Italian, Chinese")) == 2
    assert len(filter_by_cuisine(rows, "Mexican")) == 0


def test_parse_cuisine_tokens():
    assert parse_cuisine_tokens("Italian, Chinese") == ["italian", "chinese"]


def test_filter_by_budget_strict():
    rows = [
        _restaurant(band=BudgetBand.LOW),
        _restaurant(id="2", band=BudgetBand.HIGH),
    ]
    assert len(filter_by_budget(rows, Budget.LOW, relaxed=False)) == 1


def test_expanded_budget_bands_relaxation():
    bands = expanded_budget_bands(Budget.LOW)
    assert BudgetBand.MEDIUM in bands


def test_keyword_filter_soft_when_no_match():
    rows = [_restaurant(name="Pizza Place", cuisines=["Italian"])]
    result = apply_keyword_filter(rows, "sushi, ramen")
    assert len(result) == 1


def test_keyword_filter_narrows_when_match():
    rows = [
        _restaurant(name="Family Diner", cuisines=["Indian"]),
        _restaurant(id="2", name="Quick Bites", cuisines=["Fast Food"]),
    ]
    result = apply_keyword_filter(rows, "family")
    assert len(result) == 1
    assert result[0].name == "Family Diner"


def test_sort_candidates_by_rating_desc():
    rows = [
        _restaurant(id="a", rating=3.5),
        _restaurant(id="b", rating=4.8),
    ]
    sorted_rows = sort_candidates(rows, Budget.MEDIUM)
    assert sorted_rows[0].id == "b"


def test_truncate_max_candidates():
    rows = [_restaurant(id=str(i)) for i in range(30)]
    assert len(truncate(rows, 20)) == 20
