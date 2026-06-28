from src.config import Settings
from src.llm.groq_client import GROQ_BASE_URL, GROQ_DEFAULT_MODEL, settings_for_groq


def test_settings_for_groq_applies_defaults():
    settings = Settings(
        llm_provider="groq",
        llm_base_url="",
        llm_model="gpt-4o-mini",
    )
    updated = settings_for_groq(settings)
    assert updated.llm_base_url == GROQ_BASE_URL
    assert updated.llm_model == GROQ_DEFAULT_MODEL


def test_groq_api_key_alias_from_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key")
    settings = Settings(llm_api_key="")
    assert settings.llm_api_key == "gsk_test_key"
