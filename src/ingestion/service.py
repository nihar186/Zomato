"""Data ingestion orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import Settings, get_settings
from src.domain.restaurant import Restaurant
from src.ingestion.budget import assign_budget_bands, budget_band_distribution
from src.ingestion.cache import cache_exists, dicts_to_restaurants, load_cache, save_cache
from src.ingestion.indexes import RestaurantIndex, build_index
from src.ingestion.loader import load_raw_rows
from src.ingestion.normalizer import normalize_row
from src.ingestion.validator import ValidationStats, validate_rows

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    raw_count: int = 0
    valid_count: int = 0
    dropped_count: int = 0
    dropped_missing_name: int = 0
    dropped_missing_location: int = 0
    dropped_missing_city: int = 0
    dropped_missing_rating: int = 0
    dropped_invalid_rating: int = 0
    budget_distribution: Dict[str, int] = field(default_factory=dict)
    budget_percentiles: Dict[str, Any] = field(default_factory=dict)
    known_cities_count: int = 0
    from_cache: bool = False

    @classmethod
    def from_validation(
        cls,
        validation: ValidationStats,
        budget_distribution: Dict[str, int],
        known_cities_count: int,
        from_cache: bool,
        budget_percentiles: Optional[Dict[str, Any]] = None,
    ) -> "IngestionStats":
        return cls(
            raw_count=validation.raw_count,
            valid_count=validation.valid_count,
            dropped_count=validation.dropped_count,
            dropped_missing_name=validation.dropped_missing_name,
            dropped_missing_location=validation.dropped_missing_location,
            dropped_missing_city=validation.dropped_missing_city,
            dropped_missing_rating=validation.dropped_missing_rating,
            dropped_invalid_rating=validation.dropped_invalid_rating,
            budget_distribution=budget_distribution,
            budget_percentiles=budget_percentiles or {},
            known_cities_count=known_cities_count,
            from_cache=from_cache,
        )


class DataIngestionService:
    """Load, preprocess, cache, and index restaurant data."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._restaurants: list[Restaurant] = []
        self._index: Optional[RestaurantIndex] = None
        self._stats: Optional[IngestionStats] = None
        self._loaded = False

    @property
    def stats(self) -> Optional[IngestionStats]:
        return self._stats

    @property
    def index(self) -> Optional[RestaurantIndex]:
        return self._index

    def ensure_loaded(self, force_refresh: bool = False) -> list[Restaurant]:
        if self._loaded and not force_refresh:
            return self._restaurants
        return self.load(force_refresh=force_refresh)

    def load(self, force_refresh: bool = False) -> list[Restaurant]:
        cache_path = Path(self._settings.data_cache_path)

        if not force_refresh and cache_exists(cache_path):
            cached_rows = load_cache(cache_path)
            if cached_rows:
                restaurants = dicts_to_restaurants(cached_rows)
                self._apply_loaded_state(
                    restaurants,
                    IngestionStats(
                        raw_count=len(cached_rows),
                        valid_count=len(restaurants),
                        dropped_count=0,
                        budget_distribution=budget_band_distribution(cached_rows),
                        known_cities_count=len(build_index(restaurants).known_cities),
                        from_cache=True,
                    ),
                )
                logger.info("Loaded %s restaurants from cache", len(restaurants))
                return self._restaurants

        rows, stats = self._ingest_from_source()
        metadata = {
            "dataset_id": self._settings.hf_dataset_id,
            "stats": stats.__dict__,
        }
        save_cache(cache_path, rows, metadata)
        restaurants = dicts_to_restaurants(rows)
        self._apply_loaded_state(restaurants, stats)
        logger.info("Ingested %s restaurants from Hugging Face", len(restaurants))
        return self._restaurants

    def _apply_loaded_state(
        self,
        restaurants: list[Restaurant],
        stats: IngestionStats,
    ) -> None:
        self._restaurants = restaurants
        self._index = build_index(restaurants)
        self._stats = stats
        self._loaded = True

    def _ingest_from_source(self) -> tuple[list[dict[str, Any]], IngestionStats]:
        normalized: list[dict[str, Any]] = []
        raw_count = 0

        for row_index, raw_row in enumerate(load_raw_rows(self._settings.hf_dataset_id)):
            raw_count += 1
            normalized.append(normalize_row(raw_row, row_index))

        valid_rows, validation = validate_rows(normalized)
        validation.raw_count = raw_count

        percentile_meta = assign_budget_bands(
            valid_rows,
            min_city_samples=self._settings.min_city_samples_for_percentiles,
        )
        distribution = budget_band_distribution(valid_rows)
        index = build_index(dicts_to_restaurants(valid_rows))

        stats = IngestionStats.from_validation(
            validation=validation,
            budget_distribution=distribution,
            known_cities_count=len(index.known_cities),
            from_cache=False,
            budget_percentiles=percentile_meta,
        )

        logger.info(
            "Ingestion stats: raw=%s valid=%s dropped=%s bands=%s cities=%s",
            stats.raw_count,
            stats.valid_count,
            stats.dropped_count,
            stats.budget_distribution,
            stats.known_cities_count,
        )
        return valid_rows, stats
