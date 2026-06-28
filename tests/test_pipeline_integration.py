"""Integration tests using cached dataset (skipped if cache missing)."""

from pathlib import Path

import pytest

from src.config import Settings
from src.domain.preferences import Budget, UserPreferences
from src.filtering.pipeline import FilterService
from src.ingestion.service import DataIngestionService

CACHE = Path("data/cache/restaurants.parquet")


@pytest.mark.skipif(not CACHE.exists(), reason="Parquet cache not built")
def test_bangalore_italian_medium_on_cached_data():
    ingestion = DataIngestionService()
    ingestion.ensure_loaded()
    assert ingestion.index is not None

    service = FilterService(
        settings=Settings(max_candidates=20, min_candidates=3),
        known_cities=ingestion.index.known_cities,
    )
    prefs = UserPreferences(
        location="Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
    )

    import time

    start = time.perf_counter()
    result = service.apply(
        prefs,
        ingestion.ensure_loaded(),
        index=ingestion.index,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result.resolved_city == "Bangalore"
    assert len(result.candidates) > 0
    assert len(result.candidates) <= 20
    assert elapsed_ms < 500, f"Filter took {elapsed_ms:.0f} ms"
