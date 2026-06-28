from src.config import CITY_ALIASES
from src.ingestion.cities import extract_city_from_address, normalize_city
from src.ingestion.normalizer import (
    normalize_row,
    parse_cost,
    parse_cuisines,
    parse_rating,
)


def test_parse_rating_from_fraction():
    assert parse_rating("4.1/5") == 4.1


def test_parse_rating_new_returns_none():
    assert parse_rating("NEW") is None


def test_parse_cost_range():
    assert parse_cost("300-400") == 350


def test_parse_cost_plain():
    assert parse_cost("800") == 800


def test_parse_cuisines_splits_csv():
    assert parse_cuisines("North Indian, Chinese") == ["North Indian", "Chinese"]


def test_extract_city_from_address():
    assert extract_city_from_address("942, Banashankari, Bangalore") == "Bangalore"


def test_normalize_city_bengaluru_alias():
    assert normalize_city("Bengaluru") == CITY_ALIASES["bengaluru"]


def test_normalize_row_maps_hf_columns(sample_raw_row):
    row = normalize_row(sample_raw_row, row_index=1)
    assert row["name"] == "Jalsa"
    assert row["city"] == "Bangalore"
    assert row["location"] == "Banashankari"
    assert row["rating"] == 4.1
    assert row["approximate_cost_for_two"] == 800
    assert len(row["id"]) == 16
