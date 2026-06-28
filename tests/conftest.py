"""Shared pytest fixtures."""

import pytest

from src.ingestion.budget import assign_budget_bands
from src.ingestion.normalizer import normalize_row
from src.ingestion.validator import validate_rows


@pytest.fixture
def sample_raw_row() -> dict:
    return {
        "url": "https://example.com",
        "address": "942, 21st Main Road, 2nd Stage, Banashankari, Bangalore",
        "name": "Jalsa",
        "online_order": "Yes",
        "book_table": "Yes",
        "rate": "4.1/5",
        "votes": 775,
        "phone": "080 42297555",
        "location": "Banashankari",
        "rest_type": "Casual Dining",
        "dish_liked": "Pasta",
        "cuisines": "North Indian, Mughlai, Chinese",
        "approx_cost(for two people)": "800",
        "reviews_list": "[]",
        "menu_item": "[]",
        "listed_in(type)": "Buffet",
        "listed_in(city)": "Banashankari",
    }


@pytest.fixture
def sample_normalized(sample_raw_row) -> dict:
    return normalize_row(sample_raw_row, row_index=0)


@pytest.fixture
def sample_validated(sample_normalized) -> dict:
    valid, _ = validate_rows([sample_normalized])
    assert len(valid) == 1
    return valid[0]


@pytest.fixture
def budget_sample_rows() -> list[dict]:
    rows = []
    for index in range(9):
        rows.append(
            {
                "id": f"r{index}",
                "name": f"Restaurant {index}",
                "location": "Area",
                "city": "Bangalore",
                "cuisines": ["Indian"],
                "rating": 4.0,
                "approximate_cost_for_two": (index + 1) * 100,
            }
        )
    assign_budget_bands(rows, min_city_samples=3)
    return rows
