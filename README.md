# Zomato AI Restaurant Recommendation System

AI-powered restaurant recommendations using the [Zomato Hugging Face dataset](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) and an LLM (Phases 2+).

## Documentation

- [Problem context](docs/context.md)
- [Architecture](docs/architecture.md)
- [Implementation plan](docs/implementation-plan.md)
- [Edge cases](docs/edge-cases.md)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Phase 1: Data ingestion

Load and cache the dataset (first run downloads from Hugging Face; may take several minutes):

```bash
python -m src.ingestion.load
```

Force refresh (ignore Parquet cache):

```bash
python -m src.ingestion.load --refresh
```

Print sample rows:

```bash
python -m src.ingestion.load --sample 5
```

Cached data is written to `data/cache/restaurants.parquet` (gitignored).

### Cold start

| Run | What happens |
|-----|----------------|
| **First** | Downloads ~51k rows from Hugging Face, normalizes, validates, assigns budget bands, writes Parquet |
| **Later** | Loads from local Parquet in seconds |

## Phase 3: LLM recommendations (Groq)

Production LLM is **[Groq](https://groq.com/)** via an OpenAI-compatible API. Set `LLM_API_KEY` or `GROQ_API_KEY` in `.env`.

```bash
# Offline demo with mock LLM (no API key needed)
python -m src.llm.demo --provider mock --location Bangalore --budget medium --cuisine Italian

# With Groq
export LLM_PROVIDER=groq LLM_API_KEY=gsk_...
python -m src.llm.demo
```

## Phase 4: REST API

Full orchestration: filter → Groq recommend → formatted JSON response.

```bash
uvicorn src.api.app:app --reload --port 8000

curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"location":"Bangalore","budget":"medium","cuisine":"Italian","min_rating":4.0}'
```

OpenAPI docs: http://127.0.0.1:8000/docs

## Phase 2: Filter pipeline

Run filters against cached data:

```bash
python -m src.filtering.demo --location Bangalore --budget medium --cuisine Italian --min-rating 4.0
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Status, dataset load info, Groq model |
| GET | `/health/ready` | Readiness probe (503 until data loaded) |
| GET | `/api/v1/cities` | Known cities |
| POST | `/api/v1/candidates` | Filter only (no LLM) |
| POST | `/api/v1/recommendations` | Filter + Groq ranked results |
| GET | `/docs` | OpenAPI Swagger UI |

## Phase 6A: Manual QA

Run 10 scripted scenarios (happy path, edge cases, degraded mode) before UI walkthrough:

```bash
# In-process (no server required; uses Groq if LLM_API_KEY is set)
python -m src.qa

# Against a running API
uvicorn src.api.app:app --reload --port 8000
python -m src.qa --mode api --base-url http://127.0.0.1:8000
```

Open http://127.0.0.1:8000/ for the UI and check the manual review items printed by the script.

## Tests

```bash
pytest -v
```

Unit tests use fixtures only (no network). Integration with Hugging Face is via the CLI above.

## Project structure

```text
src/
  domain/          # Restaurant, UserPreferences, Recommendation
  ingestion/       # Loader, normalizer, validator, budget, cache, service
  api/             # FastAPI app
  filtering/       # Phase 2
  llm/             # Phase 3
tests/
data/cache/        # Generated Parquet (gitignored)
```
