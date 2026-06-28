import pytest

from src.domain.preferences import Budget, UserPreferences
from src.filtering.preferences_validator import PreferenceValidationError, PreferenceValidator


def test_resolve_exact_city():
    validator = PreferenceValidator(known_cities=["Bangalore", "Delhi"])
    prefs = UserPreferences(location="bangalore", budget=Budget.MEDIUM)
    resolved = validator.resolve(prefs)
    assert resolved.resolved_city == "Bangalore"


def test_resolve_bengaluru_alias():
    validator = PreferenceValidator(known_cities=["Bangalore"])
    prefs = UserPreferences(location="Bengaluru", budget=Budget.LOW)
    resolved = validator.resolve(prefs)
    assert resolved.resolved_city == "Bangalore"


def test_unknown_city_raises_with_suggestions():
    validator = PreferenceValidator(known_cities=["Bangalore", "Delhi"])
    prefs = UserPreferences(location="Tokyo", budget=Budget.LOW)
    with pytest.raises(PreferenceValidationError) as exc_info:
        validator.resolve(prefs)
    assert exc_info.value.suggestions
