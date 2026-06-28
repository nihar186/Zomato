from pathlib import Path

from src.ingestion.budget import assign_budget_bands
from src.ingestion.cache import cache_exists, dicts_to_restaurants, load_cache, save_cache
from src.ingestion.validator import validate_rows


def test_cache_round_trip(tmp_path: Path, sample_normalized):
    valid, _ = validate_rows([sample_normalized])
    assign_budget_bands(valid, min_city_samples=1)
    cache_file = tmp_path / "restaurants.parquet"

    save_cache(cache_file, valid, metadata={"test": True})
    assert cache_exists(cache_file)

    loaded = load_cache(cache_file)
    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0]["name"] == "Jalsa"

    restaurants = dicts_to_restaurants(loaded)
    assert restaurants[0].city == "Bangalore"
    assert restaurants[0].budget_band.value in {"low", "medium", "high", "unknown"}


def test_cache_handles_nan_cost(tmp_path: Path, sample_normalized):
    valid, _ = validate_rows([sample_normalized])
    valid[0]["approximate_cost_for_two"] = float("nan")
    valid[0]["budget_band"] = "unknown"
    cache_file = tmp_path / "nan.parquet"
    save_cache(cache_file, valid, metadata={})
    loaded = load_cache(cache_file)
    restaurants = dicts_to_restaurants(loaded)
    assert restaurants[0].approximate_cost_for_two is None
