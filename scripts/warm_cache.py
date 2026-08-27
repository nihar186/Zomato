#!/usr/bin/env python3
"""Build the parquet cache during Docker image build (more RAM available than runtime)."""

from __future__ import annotations

import os

os.environ.setdefault("INCLUDE_RAW_ATTRIBUTES", "false")

from src.config import get_settings
from src.ingestion.service import DataIngestionService


def main() -> None:
    settings = get_settings()
    service = DataIngestionService(settings)
    restaurants = service.load(force_refresh=True)
    print(f"Cache ready: {len(restaurants)} restaurants -> {settings.data_cache_path}")


if __name__ == "__main__":
    main()
