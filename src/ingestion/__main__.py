"""CLI: python -m src.ingestion.load [--refresh] [--sample N]"""

from __future__ import annotations

import argparse
import logging
import sys

from src.ingestion.service import DataIngestionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Load and cache Zomato restaurant data.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore cache and re-download from Hugging Face.",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Print N sample restaurants after load (0 = skip).",
    )
    args = parser.parse_args()

    service = DataIngestionService()
    restaurants = service.load(force_refresh=args.refresh)
    stats = service.stats
    index = service.index

    print(f"Loaded {len(restaurants)} restaurants (from_cache={stats.from_cache if stats else False})")
    if stats:
        print(f"  raw={stats.raw_count} valid={stats.valid_count} dropped={stats.dropped_count}")
        print(f"  budget_distribution={stats.budget_distribution}")
        print(f"  known_cities={stats.known_cities_count}")

    if index and index.known_cities:
        preview = index.known_cities[:10]
        print(f"  sample cities: {preview}{'...' if len(index.known_cities) > 10 else ''}")

    if args.sample > 0:
        for restaurant in restaurants[: args.sample]:
            print(
                f"- {restaurant.name} | {restaurant.city} | "
                f"{restaurant.rating} | {restaurant.budget_band.value} | "
                f"{', '.join(restaurant.cuisines[:3])}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
