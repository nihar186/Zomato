from pathlib import Path
from unittest.mock import patch

from src.config import Settings
from src.ingestion.service import DataIngestionService


def _make_raw_rows(count: int = 3) -> list[dict]:
    rows = []
    for index in range(count):
        rows.append(
            {
                "url": f"https://example.com/{index}",
                "address": f"Street, Area, Bangalore",
                "name": f"Restaurant {index}",
                "rate": "4.0/5",
                "location": "Area",
                "cuisines": "Indian, Chinese",
                "approx_cost(for two people)": str(200 * (index + 1)),
                "listed_in(city)": "Area",
            }
        )
    return rows


def test_service_ingest_and_cache(tmp_path: Path):
    settings = Settings(data_cache_path=tmp_path / "restaurants.parquet")
    service = DataIngestionService(settings=settings)

    with patch("src.ingestion.service.load_raw_rows", return_value=iter(_make_raw_rows())):
        restaurants = service.load(force_refresh=True)

    assert len(restaurants) == 3
    assert all(r.id for r in restaurants)
    assert all(r.city == "Bangalore" for r in restaurants)
    assert service.stats is not None
    assert service.stats.valid_count == 3
    assert service.index is not None
    assert "Bangalore" in service.index.known_cities

    # Second load should hit cache
    service2 = DataIngestionService(settings=settings)
    cached = service2.load(force_refresh=False)
    assert len(cached) == 3
    assert service2.stats is not None
    assert service2.stats.from_cache is True
