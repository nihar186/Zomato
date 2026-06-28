from src.api.formatter import to_recommendations_response
from src.domain.recommendation import Recommendation, RecommendationMeta, RecommendationResponse


def test_to_recommendations_response():
    domain = RecommendationResponse(
        summary="Summary text",
        recommendations=[
            Recommendation(
                rank=1,
                restaurant_id="abc",
                name="Cafe",
                cuisine="Italian",
                rating=4.5,
                estimated_cost="₹600 for two",
                explanation="Great fit.",
            )
        ],
        meta=RecommendationMeta(
            candidates_considered=10,
            filters_relaxed=True,
            degraded_mode=False,
        ),
    )
    api = to_recommendations_response(domain, resolved_city="Bangalore")
    assert api.summary == "Summary text"
    assert api.meta.candidates_considered == 10
    assert api.meta.filters_relaxed is True
    assert api.meta.resolved_city == "Bangalore"
    assert api.recommendations[0].estimated_cost == "₹600 for two"
