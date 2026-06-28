"""Zomato AI Culinary Concierge — Streamlit Frontend."""

from __future__ import annotations

import logging

import streamlit as st

from src.config import Settings, get_settings
from src.domain.preferences import Budget, UserPreferences
from src.filtering.pipeline import FilterService
from src.ingestion.service import DataIngestionService
from src.llm.client import create_llm_client
from src.llm.engine import RecommendationEngine
from src.api.orchestrator import RecommendationOrchestrator

logger = logging.getLogger(__name__)

BUDGET_LABELS = {"low": "₹ Low", "medium": "₹₹ Medium", "high": "₹₹₹ High"}


def init_services() -> tuple[DataIngestionService, RecommendationOrchestrator]:
    """Initialize and cache all services in session state."""
    if "orchestrator" in st.session_state:
        return st.session_state["ingestion"], st.session_state["orchestrator"]

    settings = get_settings()
    ingestion = DataIngestionService(settings)

    # On Streamlit Cloud the filesystem is ephemeral — the parquet cache won't
    # persist between deploys.  If the cache file is missing, force a fresh
    # download from HuggingFace (adds ~30-60 s to cold start).
    from pathlib import Path
    if not Path(settings.data_cache_path).exists():
        ingestion.ensure_loaded(force_refresh=True)
    else:
        ingestion.ensure_loaded()

    index = ingestion.index
    filter_service = FilterService(
        settings=settings,
        known_cities=index.known_cities if index else None,
    )
    llm_client = create_llm_client(settings)
    engine = RecommendationEngine(settings, llm_client=llm_client)
    orchestrator = RecommendationOrchestrator(
        ingestion,
        filter_service,
        engine=engine,
        settings=settings,
    )

    st.session_state["ingestion"] = ingestion
    st.session_state["orchestrator"] = orchestrator
    st.session_state["settings"] = settings
    return ingestion, orchestrator


def render_recommendation_card(rec) -> None:
    """Render a single recommendation card."""
    with st.container(border=True):
        header_col, rank_col = st.columns([6, 1])
        with header_col:
            st.subheader(rec.name)
        with rank_col:
            st.markdown(
                f"<h3 style='text-align:center; color:#E23744;'>#{rec.rank}</h3>",
                unsafe_allow_html=True,
            )

        tag_col1, tag_col2, tag_col3 = st.columns(3)
        with tag_col1:
            st.caption(f"🍜 {rec.cuisine}")
        with tag_col2:
            st.caption(f"⭐ {rec.rating}")
        with tag_col3:
            st.caption(f"💰 {rec.estimated_cost}")

        st.markdown(f"> {rec.explanation}")


def main() -> None:
    st.set_page_config(
        page_title="Zomato AI — Culinary Concierge",
        page_icon="🍽️",
        layout="wide",
    )

    st.title("🍽️ Zomato AI — Culinary Concierge")
    st.caption("AI-powered restaurant recommendations with Groq LLM ranking")

    # --- Initialize services ---
    with st.spinner("Loading restaurant data..."):
        ingestion, orchestrator = init_services()

    settings: Settings = st.session_state.get("settings", get_settings())
    index = ingestion.index

    # --- Preference Form ---
    with st.form("preferences_form"):
        col1, col2 = st.columns(2)

        with col1:
            cities = index.known_cities if index else []
            location = st.selectbox(
                "📍 City",
                options=cities,
                index=None,
                placeholder="Select a city...",
            )
            cuisine = st.text_input(
                "🍕 Craving / Cuisine",
                placeholder="e.g. Italian, Biryani, Cafe...",
            )

        with col2:
            budget_options = ["low", "medium", "high"]
            budget_choice = st.radio(
                "💰 Budget",
                options=budget_options,
                index=1,
                horizontal=True,
                format_func=lambda x: BUDGET_LABELS[x],
            )
            min_rating = st.slider(
                "⭐ Minimum Rating",
                min_value=2.0,
                max_value=5.0,
                value=4.0,
                step=0.1,
            )

        additional = st.text_area(
            "📝 Special Instructions",
            placeholder="Dietary restrictions, seating, family-friendly...",
            height=68,
        )

        submitted = st.form_submit_button(
            "✨ Find Recommendations",
            type="primary",
            use_container_width=True,
        )

    # --- Process Request ---
    if submitted:
        if not location:
            st.error("Please select a city.")
            return

        preferences = UserPreferences(
            location=location,
            budget=Budget(budget_choice),
            cuisine=cuisine or None,
            min_rating=min_rating,
            additional_preferences=additional or None,
        )

        with st.spinner("🤖 Curating your experience..."):
            try:
                outcome = orchestrator.recommend(preferences)
            except Exception as exc:
                logger.exception("Recommendation failed")
                st.error(f"Something went wrong: {exc}")
                return

        response = outcome.response

        # --- Summary ---
        if response.summary:
            st.info(response.summary)

        # --- Meta chips ---
        meta_col1, meta_col2, meta_col3 = st.columns(3)
        with meta_col1:
            st.metric("Scanned", outcome.filter_result.candidates_considered)
        with meta_col2:
            st.metric(
                "Filters Relaxed",
                "Yes" if outcome.filter_result.filters_relaxed else "No",
            )
        with meta_col3:
            st.metric(
                "Mode",
                "Degraded" if response.meta.degraded_mode else "Groq LLM",
            )

        if response.meta.degraded_mode:
            st.warning(
                "⚠️ Running in degraded mode — LLM unavailable. "
                "Showing filter-based rankings."
            )

        # --- Recommendation Cards ---
        if not response.recommendations:
            st.warning(
                "No restaurants matched your criteria. "
                "Try broadening your budget or cuisine."
            )
            if outcome.filter_result.city_suggestions:
                st.info(
                    f"Did you mean: {', '.join(outcome.filter_result.city_suggestions)}?"
                )
            return

        for rec in response.recommendations:
            render_recommendation_card(rec)


if __name__ == "__main__":
    main()
