import pytest
from pydantic import ValidationError

from src.api.schemas import RecommendationRequest
from src.domain.preferences import Budget


def test_request_sanitizes_html_tags():
    # Attempt to inject HTML tags into input strings
    request = RecommendationRequest(
        location="<script>alert('xss')</script>Bangalore",
        budget=Budget.MEDIUM,
        cuisine="Italian<b>cuisine</b>",
        additional_preferences="<a href='http://evil.com'>family-friendly</a> and fast service",
    )
    
    assert request.location == "alert('xss')Bangalore"
    assert request.cuisine == "Italiancuisine"
    assert request.additional_preferences == "family-friendly and fast service"


def test_request_collapses_whitespace():
    request = RecommendationRequest(
        location="  Bangalore   ",
        budget=Budget.MEDIUM,
        cuisine="  Italian  Pizza  ",
        additional_preferences="   fast    service  ",
    )
    assert request.location == "Bangalore"
    assert request.cuisine == "Italian Pizza"
    assert request.additional_preferences == "fast service"


def test_request_enforces_length_limits():
    # Location limit: 50 characters
    with pytest.raises(ValidationError) as exc:
        RecommendationRequest(
            location="A" * 51,
            budget=Budget.MEDIUM,
        )
    assert "String should have at most 50 characters" in str(exc.value)

    # Cuisine limit: 100 characters
    with pytest.raises(ValidationError) as exc:
        RecommendationRequest(
            location="Bangalore",
            budget=Budget.MEDIUM,
            cuisine="C" * 101,
        )
    assert "String should have at most 100 characters" in str(exc.value)

    # Additional preferences limit: 500 characters
    with pytest.raises(ValidationError) as exc:
        RecommendationRequest(
            location="Bangalore",
            budget=Budget.MEDIUM,
            additional_preferences="P" * 501,
        )
    assert "String should have at most 500 characters" in str(exc.value)
