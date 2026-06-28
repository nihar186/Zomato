"""Compute budget bands from cost percentiles."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import numpy as np

from src.domain.restaurant import BudgetBand


def _percentiles(values: list[int]) -> tuple[float, float]:
    array = np.array(values, dtype=float)
    p33, p66 = np.percentile(array, [33, 66])
    return float(p33), float(p66)


def assign_budget_bands(
    rows: list[dict],
    min_city_samples: int = 30,
) -> dict[str, dict[str, float]]:
    """
    Assign budget_band on each row in place.
    Returns percentile metadata per scope (global and per city).
    """
    costs_by_city: dict[str, list[int]] = defaultdict(list)
    global_costs: list[int] = []

    for row in rows:
        cost = row.get("approximate_cost_for_two")
        if cost is None:
            continue
        city = row.get("city") or ""
        costs_by_city[city].append(int(cost))
        global_costs.append(int(cost))

    if not global_costs:
        for row in rows:
            row["budget_band"] = BudgetBand.UNKNOWN.value
        return {}

    global_p33, global_p66 = _percentiles(global_costs)
    metadata: dict[str, dict[str, float]] = {
        "__global__": {"p33": global_p33, "p66": global_p66}
    }

    city_thresholds: dict[str, tuple[float, float]] = {}
    for city, costs in costs_by_city.items():
        if len(costs) >= min_city_samples:
            city_thresholds[city] = _percentiles(costs)
            p33, p66 = city_thresholds[city]
            metadata[city] = {"p33": p33, "p66": p66}

    for row in rows:
        cost = row.get("approximate_cost_for_two")
        if cost is None:
            row["budget_band"] = BudgetBand.UNKNOWN.value
            continue

        city = row.get("city") or ""
        if city in city_thresholds:
            p33, p66 = city_thresholds[city]
        else:
            p33, p66 = global_p33, global_p66

        if cost <= p33:
            row["budget_band"] = BudgetBand.LOW.value
        elif cost <= p66:
            row["budget_band"] = BudgetBand.MEDIUM.value
        else:
            row["budget_band"] = BudgetBand.HIGH.value

    return metadata


def budget_band_distribution(rows: Iterable[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        band = row.get("budget_band", BudgetBand.UNKNOWN.value)
        counts[str(band)] += 1
    return dict(counts)
