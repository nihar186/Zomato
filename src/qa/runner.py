"""Execute Phase 6A manual QA scenarios."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
from pydantic import ValidationError

from src.api.orchestrator import RecommendationOrchestrator
from src.api.schemas import RecommendationRequest
from src.config import Settings, get_settings
from src.domain.preferences import UserPreferences
from src.filtering.pipeline import FilterService
from src.filtering.preferences_validator import PreferenceValidationError
from src.ingestion.service import DataIngestionService
from src.llm.client import create_llm_client
from src.llm.engine import RecommendationEngine
from src.qa.scenarios import MANUAL_SCENARIOS, ManualScenario


@dataclass
class QAServices:
    orchestrator: RecommendationOrchestrator
    filter_service: FilterService
    ingestion: DataIngestionService
    degraded_orchestrator: RecommendationOrchestrator


@dataclass
class ScenarioResult:
    scenario: ManualScenario
    passed: bool
    status_code: int
    duration_ms: float
    checks: List[str] = field(default_factory=list)
    response_preview: str = ""
    error: Optional[str] = None


def _build_services(settings: Settings) -> QAServices:
    ingestion = DataIngestionService(settings)
    ingestion.ensure_loaded()
    index = ingestion.index
    if index is None:
        raise RuntimeError("Restaurant index is not ready. Run: python -m src.ingestion.load")

    filter_service = FilterService(settings=settings, known_cities=index.known_cities)
    engine = RecommendationEngine(settings, llm_client=create_llm_client(settings))
    orchestrator = RecommendationOrchestrator(ingestion, filter_service, engine, settings)

    degraded_settings = settings.model_copy(update={"llm_provider": "groq", "llm_api_key": ""})
    degraded_engine = RecommendationEngine(degraded_settings, llm_client=create_llm_client(degraded_settings))
    degraded_orchestrator = RecommendationOrchestrator(
        ingestion, filter_service, degraded_engine, degraded_settings
    )

    return QAServices(
        orchestrator=orchestrator,
        filter_service=filter_service,
        ingestion=ingestion,
        degraded_orchestrator=degraded_orchestrator,
    )



def _run_local_scenario(scenario: ManualScenario, services: QAServices) -> ScenarioResult:
    start = time.perf_counter()
    status_code = 200
    body: Dict[str, Any] = {}

    try:
        try:
            request = RecommendationRequest(**scenario.payload)
        except ValidationError as exc:
            status_code = 422
            body = {"detail": exc.errors()}
            duration_ms = (time.perf_counter() - start) * 1000
            passed, checks = _evaluate_scenario(scenario, status_code, body)
            return ScenarioResult(
                scenario=scenario,
                passed=passed,
                status_code=status_code,
                duration_ms=duration_ms,
                checks=checks,
                response_preview=_format_preview(body),
            )

        prefs = UserPreferences(
            location=request.location,
            budget=request.budget,
            cuisine=request.cuisine,
            min_rating=request.min_rating,
            additional_preferences=request.additional_preferences,
        )

        if scenario.endpoint == "/api/v1/candidates":
            filter_result = services.filter_service.apply(
                prefs,
                services.ingestion.ensure_loaded(),
                index=services.ingestion.index,
            )
            body = {
                "candidates": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "rating": r.rating,
                        "budget_band": r.budget_band.value,
                        "cuisines": r.cuisines,
                    }
                    for r in filter_result.candidates
                ],
                "meta": {
                    "candidates_considered": filter_result.candidates_considered,
                    "filters_relaxed": filter_result.filters_relaxed,
                    "resolved_city": filter_result.resolved_city,
                },
            }
        else:
            active = (
                services.degraded_orchestrator
                if scenario.force_degraded
                else services.orchestrator
            )
            outcome = active.recommend(prefs)
            body = {
                "summary": outcome.response.summary,
                "recommendations": [
                    {
                        "rank": item.rank,
                        "name": item.name,
                        "rating": item.rating,
                        "estimated_cost": item.estimated_cost,
                        "explanation": item.explanation,
                    }
                    for item in outcome.response.recommendations
                ],
                "meta": {
                    "candidates_considered": outcome.response.meta.candidates_considered,
                    "filters_relaxed": outcome.response.meta.filters_relaxed,
                    "degraded_mode": outcome.response.meta.degraded_mode,
                    "resolved_city": outcome.filter_result.resolved_city,
                },
            }
    except PreferenceValidationError as exc:
        status_code = 400
        body = {"detail": {"message": str(exc), "suggestions": exc.suggestions}}
    except Exception as exc:  # pragma: no cover - surfaced in manual QA output
        return ScenarioResult(
            scenario=scenario,
            passed=False,
            status_code=500,
            duration_ms=(time.perf_counter() - start) * 1000,
            error=str(exc),
        )

    duration_ms = (time.perf_counter() - start) * 1000
    passed, checks = _evaluate_scenario(scenario, status_code, body)
    preview = _format_preview(body)
    return ScenarioResult(
        scenario=scenario,
        passed=passed,
        status_code=status_code,
        duration_ms=duration_ms,
        checks=checks,
        response_preview=preview,
    )


def _run_api_scenario(scenario: ManualScenario, base_url: str) -> ScenarioResult:
    start = time.perf_counter()
    url = f"{base_url.rstrip('/')}{scenario.endpoint}"
    try:
        response = httpx.post(url, json=scenario.payload, timeout=60.0)
    except httpx.HTTPError as exc:
        return ScenarioResult(
            scenario=scenario,
            passed=False,
            status_code=0,
            duration_ms=(time.perf_counter() - start) * 1000,
            error=f"HTTP request failed: {exc}",
        )

    duration_ms = (time.perf_counter() - start) * 1000
    try:
        body = response.json()
    except json.JSONDecodeError:
        body = {"raw": response.text[:500]}

    passed, checks = _evaluate_scenario(scenario, response.status_code, body)
    return ScenarioResult(
        scenario=scenario,
        passed=passed,
        status_code=response.status_code,
        duration_ms=duration_ms,
        checks=checks,
        response_preview=_format_preview(body),
    )


def _evaluate_scenario(
    scenario: ManualScenario,
    status_code: int,
    body: Dict[str, Any],
) -> tuple[bool, List[str]]:
    checks: List[str] = []
    passed = True

    if status_code != scenario.expect_status:
        passed = False
        checks.append(f"FAIL status {status_code} (expected {scenario.expect_status})")
    else:
        checks.append(f"PASS status {status_code}")

    meta = body.get("meta") or {}
    results = body.get("recommendations") or body.get("candidates") or []

    if scenario.expect_min_results and status_code == 200:
        if len(results) >= scenario.expect_min_results:
            checks.append(f"PASS result_count={len(results)}")
        else:
            passed = False
            checks.append(
                f"FAIL result_count={len(results)} (expected >= {scenario.expect_min_results})"
            )

    if scenario.expect_degraded is not None and status_code == 200:
        degraded = bool(meta.get("degraded_mode"))
        if degraded == scenario.expect_degraded:
            checks.append(f"PASS degraded_mode={degraded}")
        else:
            passed = False
            checks.append(
                f"FAIL degraded_mode={degraded} (expected {scenario.expect_degraded})"
            )

    if scenario.expect_filters_relaxed is not None and status_code == 200:
        relaxed = bool(meta.get("filters_relaxed"))
        if relaxed == scenario.expect_filters_relaxed:
            checks.append(f"PASS filters_relaxed={relaxed}")
        else:
            passed = False
            checks.append(
                f"FAIL filters_relaxed={relaxed} (expected {scenario.expect_filters_relaxed})"
            )

    if scenario.id == "QA-05" and status_code == 200:
        min_rating = scenario.payload.get("min_rating", 0)
        bad = [r for r in results if r.get("rating", 0) < min_rating]
        if bad:
            passed = False
            checks.append(f"FAIL {len(bad)} results below min_rating {min_rating}")
        else:
            checks.append(f"PASS all ratings >= {min_rating}")

    return passed, checks


def _format_preview(body: Dict[str, Any]) -> str:
    if "recommendations" in body:
        lines = []
        if body.get("summary"):
            lines.append(f"summary: {body['summary'][:160]}")
        meta = body.get("meta") or {}
        lines.append(
            "meta: "
            f"candidates={meta.get('candidates_considered')} "
            f"relaxed={meta.get('filters_relaxed')} "
            f"degraded={meta.get('degraded_mode')}"
        )
        for item in body.get("recommendations", [])[:3]:
            lines.append(
                f"  #{item.get('rank')} {item.get('name')} "
                f"({item.get('rating')}) — {item.get('estimated_cost')}"
            )
            explanation = item.get("explanation") or ""
            lines.append(f"     {explanation[:120]}")
        return "\n".join(lines)

    if "candidates" in body:
        meta = body.get("meta") or {}
        lines = [
            f"candidates: {len(body['candidates'])} considered={meta.get('candidates_considered')}"
        ]
        for item in body.get("candidates", [])[:3]:
            lines.append(
                f"  {item.get('name')} ({item.get('rating')}) band={item.get('budget_band')}"
            )
        return "\n".join(lines)

    if "detail" in body:
        detail = body["detail"]
        if isinstance(detail, dict):
            return f"detail: {detail.get('message', detail)}"
        return f"detail: {detail}"

    return json.dumps(body, indent=2)[:600]


def run_manual_qa(
    *,
    mode: str = "local",
    base_url: str = "http://127.0.0.1:8000",
    scenario_ids: Optional[List[str]] = None,
) -> List[ScenarioResult]:
    """Run all (or selected) manual QA scenarios."""
    scenarios = MANUAL_SCENARIOS
    if scenario_ids:
        wanted = {s.upper() for s in scenario_ids}
        scenarios = [s for s in scenarios if s.id in wanted]

    results: List[ScenarioResult] = []
    services: Optional[QAServices] = None

    if mode == "local":
        services = _build_services(get_settings())

    for scenario in scenarios:
        if mode == "api":
            result = _run_api_scenario(scenario, base_url)
        else:
            assert services is not None
            result = _run_local_scenario(scenario, services)
        results.append(result)

    return results


def print_report(results: List[ScenarioResult]) -> int:
    """Print human-readable QA report; return exit code."""
    passed_count = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n=== Phase 6A Manual QA ===\n")
    for result in results:
        scenario = result.scenario
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {scenario.id} — {scenario.name}")
        print(f"       {scenario.description}")
        print(f"       duration={result.duration_ms:.0f}ms")
        for check in result.checks:
            print(f"       • {check}")
        if result.error:
            print(f"       • ERROR: {result.error}")
        if result.response_preview:
            print("       response:")
            for line in result.response_preview.splitlines():
                print(f"         {line}")
        if scenario.manual_checks:
            print("       manual review:")
            for item in scenario.manual_checks:
                print(f"         [ ] {item}")
        print()

    print(f"Automated pre-checks: {passed_count}/{total} passed")
    print("\nNext: open http://127.0.0.1:8000/ and walk through the same scenarios in the UI.")
    print("Mark manual review items above once explanations feel personalized.\n")
    return 0 if passed_count == total else 1


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Phase 6A manual QA runner")
    parser.add_argument(
        "--mode",
        choices=["local", "api"],
        default="local",
        help="local = in-process orchestrator; api = HTTP against running server",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--scenario", action="append", dest="scenarios", help="Run one scenario id")
    args = parser.parse_args(argv)

    results = run_manual_qa(
        mode=args.mode,
        base_url=args.base_url,
        scenario_ids=args.scenarios,
    )
    return print_report(results)


if __name__ == "__main__":
    raise SystemExit(main())
