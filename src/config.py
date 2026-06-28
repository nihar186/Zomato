"""Application configuration — supports .env and Streamlit secrets."""

import sys
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"

# City name aliases applied during ingestion (lowercase key -> canonical value).
CITY_ALIASES: dict[str, str] = {
    "bengaluru": "Bangalore",
    "bangalore": "Bangalore",
    "bangalore.": "Bangalore",
    "banglore": "Bangalore",
    "bengalore": "Bangalore",
    "new delhi": "Delhi",
    "delhi-ncr": "Delhi",
    "gurgaon": "Gurgaon",
    "gurugram": "Gurgaon",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "chennai": "Chennai",
    "madras": "Chennai",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "ahmedabad": "Ahmedabad",
    "noida": "Noida",
    "ghaziabad": "Ghaziabad",
}


def _is_streamlit_runtime() -> bool:
    """Return True if we are running inside a Streamlit server process."""
    # When launched via `streamlit run`, Streamlit sets specific markers
    # on sys.argv or the environment that we can detect.
    if "streamlit" in sys.argv[0].lower():
        return True
    # Streamlit Cloud and `streamlit run` both set this env var
    import os
    if os.environ.get("STREAMLIT_SERVER_HEADLESS") or os.environ.get("IS_STREAMLIT"):
        return True
    return False


def _get_streamlit_secrets() -> dict[str, str]:
    """Load secrets from Streamlit if running inside Streamlit; return empty otherwise.

    When running via ``streamlit run``, use ``st.secrets`` (which reads both
    the local ``.streamlit/secrets.toml`` and cloud-managed secrets).

    When NOT inside Streamlit (e.g. pytest, uvicorn), return an empty dict so
    that ``.env`` / environment variables are the sole config source and no
    env-var pollution occurs.
    """
    if not _is_streamlit_runtime():
        return {}

    try:
        import streamlit as st
        return dict(st.secrets)
    except Exception:
        return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hf_dataset_id: str = "ManikaSaini/zomato-restaurant-recommendation"
    data_cache_path: Path = Path("data/cache/restaurants.parquet")
    max_candidates: int = 20
    min_candidates: int = 3
    top_n_results: int = 5
    llm_provider: str = "groq"
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "GROQ_API_KEY"),
    )
    llm_model: str = GROQ_DEFAULT_MODEL
    llm_base_url: str = GROQ_BASE_URL
    cors_origins: str = "*"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 1500
    llm_timeout_seconds: float = 30.0
    llm_log_prompts: bool = False
    llm_log_dir: Path = Path("data/logs/llm")
    min_city_samples_for_percentiles: int = 30


def get_settings() -> Settings:
    """Build Settings from .env, environment variables, and Streamlit secrets.

    Streamlit secrets are injected as explicit keyword arguments to the
    Settings constructor rather than mutating os.environ, so they don't
    leak across test boundaries or interfere with monkeypatch.
    """
    streamlit_overrides = _get_streamlit_secrets()
    # Map Streamlit secret keys to Settings field names (lowercase by convention)
    kwargs = {}
    for key, value in streamlit_overrides.items():
        field_name = key.lower()
        if field_name in Settings.model_fields:
            kwargs[field_name] = value
        # Also check aliases: LLM_API_KEY / GROQ_API_KEY → llm_api_key
        for fname, field_info in Settings.model_fields.items():
            alias_choices = field_info.validation_alias
            if isinstance(alias_choices, AliasChoices):
                for alias in alias_choices.choices:
                    if isinstance(alias, str) and alias == key:
                        kwargs[fname] = value
    return Settings(**kwargs)
