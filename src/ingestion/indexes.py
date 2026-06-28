"""In-memory indexes for restaurants."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from src.domain.restaurant import Restaurant


@dataclass
class RestaurantIndex:
    by_city: dict[str, list[Restaurant]] = field(default_factory=dict)
    by_cuisine_token: dict[str, list[Restaurant]] = field(default_factory=dict)
    known_cities: list[str] = field(default_factory=list)

    def get_by_city(self, city: str) -> list[Restaurant]:
        return self.by_city.get(city, [])


def build_index(restaurants: list[Restaurant]) -> RestaurantIndex:
    by_city: dict[str, list[Restaurant]] = defaultdict(list)
    by_cuisine: dict[str, list[Restaurant]] = defaultdict(list)

    for restaurant in restaurants:
        city_key = restaurant.city.strip()
        if city_key:
            by_city[city_key].append(restaurant)

        loc_key = restaurant.location.strip()
        if loc_key and loc_key.lower() != city_key.lower():
            by_city[loc_key].append(restaurant)

        seen_tokens: set[str] = set()
        for cuisine in restaurant.cuisines:
            token = cuisine.strip().lower()
            if token and token not in seen_tokens:
                seen_tokens.add(token)
                by_cuisine[token].append(restaurant)

    known_cities = sorted(by_city.keys(), key=str.lower)
    return RestaurantIndex(
        by_city=dict(by_city),
        by_cuisine_token=dict(by_cuisine),
        known_cities=known_cities,
    )

