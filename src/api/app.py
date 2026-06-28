"""FastAPI application — Phase 4 API & orchestration."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.formatter import empty_reason_from_filter, to_recommendations_response
from src.api.middleware import RequestLoggingMiddleware
from src.api.orchestrator import RecommendationOrchestrator
from src.api.schemas import (
    CandidateOut,
    CandidatesResponse,
    FilterMetaOut,
    RecommendationRequest,
    RecommendationsResponse,
)
from src.config import Settings, get_settings
from src.domain.preferences import UserPreferences
from src.filtering.pipeline import FilterService
from src.filtering.preferences_validator import PreferenceValidationError
from src.ingestion.service import DataIngestionService
from src.llm.client import create_llm_client
from src.llm.engine import RecommendationEngine

logger = logging.getLogger(__name__)

_settings: Settings = get_settings()
_ingestion: Optional[DataIngestionService] = None
_filter_service: Optional[FilterService] = None
_orchestrator: Optional[RecommendationOrchestrator] = None
_ready: bool = False


import asyncio
from concurrent.futures import ThreadPoolExecutor

async def _load_data_background():
    global _ingestion, _filter_service, _orchestrator, _ready, _settings
    try:
        # Run the blocking read in a thread pool to avoid blocking the asyncio event loop
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, _ingestion.ensure_loaded)
        
        index = _ingestion.index
        _filter_service = FilterService(
            settings=_settings,
            known_cities=index.known_cities if index else None,
        )
        llm_client = create_llm_client(_settings)
        engine = RecommendationEngine(_settings, llm_client=llm_client)
        _orchestrator = RecommendationOrchestrator(
            _ingestion,
            _filter_service,
            engine=engine,
            settings=_settings,
        )
        _ready = True
        logger.info(
            "API ready: restaurants=%s provider=%s model=%s",
            len(_ingestion.ensure_loaded()),
            _settings.llm_provider,
            _settings.llm_model,
        )
    except Exception as exc:
        logger.exception("Failed to load restaurant data in background: %s", exc)
        _ready = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start dataset loading in the background and yield immediately."""
    global _ingestion, _settings
    _settings = get_settings()
    _ingestion = DataIngestionService(_settings)
    
    # Start loading in background task
    asyncio.create_task(_load_data_background())
    yield


app = FastAPI(
    title="Zomato Restaurant Recommendations",
    version="0.4.0",
    description="AI-powered restaurant recommendations with Groq LLM ranking.",
    lifespan=lifespan,
)

_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "message": "Validation failed."},
    )


def _require_ready() -> None:
    if not _ready or _ingestion is None or _orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Service is starting or dataset failed to load. Retry shortly.",
        )


def _get_filter_service() -> FilterService:
    _require_ready()
    assert _filter_service is not None
    return _filter_service


def _get_orchestrator() -> RecommendationOrchestrator:
    _require_ready()
    assert _orchestrator is not None
    return _orchestrator


def _to_preferences(body: RecommendationRequest) -> UserPreferences:
    return UserPreferences(
        location=body.location,
        budget=body.budget,
        cuisine=body.cuisine,
        min_rating=body.min_rating,
        additional_preferences=body.additional_preferences,
    )


@app.get("/health")
def health() -> dict:
    stats = _ingestion.stats if _ingestion else None
    return {
        "status": "ok" if _ready else "starting",
        "ready": _ready,
        "data_loaded": _ingestion.index is not None if _ingestion else False,
        "restaurant_count": len(_ingestion.ensure_loaded()) if _ingestion and _ready else 0,
        "from_cache": stats.from_cache if stats else False,
        "llm_provider": _settings.llm_provider,
        "llm_model": _settings.llm_model,
    }


@app.get("/health/ready")
def readiness() -> dict:
    if not _ready:
        raise HTTPException(status_code=503, detail="Service not ready.")
    return {"ready": True}


@app.get("/api/v1/cities")
def list_cities() -> dict:
    _require_ready()
    assert _ingestion is not None
    index = _ingestion.index
    return {"cities": index.known_cities if index else []}


@app.post("/api/v1/candidates", response_model=CandidatesResponse)
def filter_candidates(body: RecommendationRequest) -> CandidatesResponse:
    """Deterministic filter pipeline (no LLM)."""
    preferences = _to_preferences(body)
    filter_service = _get_filter_service()
    assert _ingestion is not None
    try:
        result = filter_service.apply(
            preferences,
            _ingestion.ensure_loaded(),
            index=_ingestion.index,
        )
    except PreferenceValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "suggestions": exc.suggestions},
        ) from exc

    candidates = [
        CandidateOut(
            id=r.id,
            name=r.name,
            city=r.city,
            location=r.location,
            cuisines=r.cuisines,
            rating=r.rating,
            approximate_cost_for_two=r.approximate_cost_for_two,
            budget_band=r.budget_band.value,
        )
        for r in result.candidates
    ]

    return CandidatesResponse(
        candidates=candidates,
        meta=FilterMetaOut(
            candidates_considered=result.candidates_considered,
            filters_relaxed=result.filters_relaxed,
            relaxation_steps=result.relaxation_steps,
            empty_reason=result.empty_reason,
            resolved_city=result.resolved_city,
            city_suggestions=result.city_suggestions,
        ),
    )


@app.post("/api/v1/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    request: Request,
    body: RecommendationRequest,
) -> RecommendationsResponse:
    """Filter + Groq LLM ranked recommendations with explanations."""
    preferences = _to_preferences(body)
    orchestrator = _get_orchestrator()
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        outcome = orchestrator.recommend(preferences)
    except PreferenceValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "suggestions": exc.suggestions},
        ) from exc

    logger.info(
        "request_id=%s recommendations=%s degraded=%s filter_ms=%.1f llm_ms=%.1f",
        request_id,
        len(outcome.response.recommendations),
        outcome.response.meta.degraded_mode,
        outcome.filter_duration_ms,
        outcome.llm_duration_ms,
    )

    return to_recommendations_response(
        outcome.response,
        resolved_city=outcome.filter_result.resolved_city,
        empty_reason=empty_reason_from_filter(outcome.filter_result),
    )


# Serve static frontend assets
app.mount("/assets", StaticFiles(directory="src/frontend/assets"), name="assets")


@app.get("/")
def serve_index() -> FileResponse:
    """Serve the single-page application UI."""
    return FileResponse("src/frontend/index.html")

