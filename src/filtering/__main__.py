"""CLI: python -m src.filtering.demo"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from src.domain.preferences import Budget, UserPreferences
from src.filtering.pipeline import FilterService
from src.ingestion.service import DataIngestionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run filter pipeline on cached data.")
    parser.add_argument("--location", default="Bangalore")
    parser.add_argument("--budget", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--cuisine", default="Italian")
    parser.add_argument("--min-rating", type=float, default=4.0)
    parser.add_argument("--additional", default="")
    parser.add_argument("--sample", type=int, default=5, help="Print top N candidates")
    args = parser.parse_args()

    ingestion = DataIngestionService()
    ingestion.ensure_loaded()
    index = ingestion.index
    if index is None:
        print("Dataset index not available.", file=sys.stderr)
        return 1

    preferences = UserPreferences(
        location=args.location,
        budget=Budget(args.budget),
        cuisine=args.cuisine or None,
        min_rating=args.min_rating,
        additional_preferences=args.additional or None,
    )

    filter_service = FilterService(known_cities=index.known_cities)
    result = filter_service.apply(
        preferences,
        ingestion.ensure_loaded(),
        index=index,
    )

    output = {
        "resolved_city": result.resolved_city,
        "candidates_considered": result.candidates_considered,
        "returned": len(result.candidates),
        "filters_relaxed": result.filters_relaxed,
        "relaxation_steps": result.relaxation_steps,
        "empty_reason": result.empty_reason,
    }
    print(json.dumps(output, indent=2))

    for restaurant in result.candidates[: args.sample]:
        print(
            f"- {restaurant.name} | {restaurant.rating} | "
            f"{restaurant.budget_band.value} | {', '.join(restaurant.cuisines[:3])}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
