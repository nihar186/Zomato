from src.domain.restaurant import BudgetBand
from src.ingestion.budget import assign_budget_bands, budget_band_distribution


def test_assign_budget_bands_distributes_three_levels(budget_sample_rows):
    distribution = budget_band_distribution(budget_sample_rows)
    assert distribution[BudgetBand.LOW.value] >= 1
    assert distribution[BudgetBand.MEDIUM.value] >= 1
    assert distribution[BudgetBand.HIGH.value] >= 1


def test_unknown_band_when_no_cost(sample_normalized):
    rows = [dict(sample_normalized)]
    rows[0]["approximate_cost_for_two"] = None
    assign_budget_bands(rows, min_city_samples=1)
    assert rows[0]["budget_band"] == BudgetBand.UNKNOWN.value
