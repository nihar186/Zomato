"""CLI: python -m src.llm.demo"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from src.api.orchestrator import RecommendationOrchestrator
from src.config import get_settings
from src.domain.preferences import Budget, UserPreferences
from src.filtering.pipeline import FilterService
from src.ingestion.service import DataIngestionService
from src.llm.client import create_llm_client
from src.llm.engine import RecommendationEngine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full recommendation pipeline.")
    parser.add_argument("--location", default="Bangalore")
    parser.add_argument("--budget", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--cuisine", default="Italian")
    parser.add_argument("--min-rating", type=float, default=4.0)
    parser.add_argument("--provider", default=None, help="openai | ollama | mock")
    args = parser.parse_args()

    settings = get_settings()
    if args.provider:
        settings = settings.model_copy(update={"llm_provider": args.provider})

    ingestion = DataIngestionService(settings)
    ingestion.ensure_loaded()
    index = ingestion.index
    if index is None:
        print("Index not ready.", file=sys.stderr)
        return 1

    preferences = UserPreferences(
        location=args.location,
        budget=Budget(args.budget),
        cuisine=args.cuisine or None,
        min_rating=args.min_rating,
    )

    filter_service = FilterService(settings=settings, known_cities=index.known_cities)
    engine = RecommendationEngine(settings, llm_client=create_llm_client(settings))
    orchestrator = RecommendationOrchestrator(ingestion, filter_service, engine, settings)

    result = orchestrator.recommend(preferences)
    import dataclasses
    print(json.dumps(dataclasses.asdict(result), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
