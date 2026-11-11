"""Typed settings read from environment variables and `.env`."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every variable in the design's "Configuration" table.

    Model names are placeholders on purpose: pick them with the editor eval.
    API keys for hosted providers are read by LiteLLM straight from the
    environment, so they are not fields here.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "sqlite:///./data/app.db"
    # Empty until the auth section, which refuses to start without a real value.
    session_secret: str = ""

    oidc_issuer: str = "http://localhost:9000/application/o/vocab-coach/"
    oidc_client_id: str = ""
    oidc_client_secret: str = ""

    llm_partner_model: str = ""
    llm_editor_model: str = ""
    llm_usage_judge_model: str = ""
    llm_drill_gen_model: str = ""
    llm_drill_grade_model: str = ""
    llm_group_gen_model: str = ""
    ollama_api_base: str = "http://localhost:11434"

    llm_partner_prompt_version: int = 1
    llm_editor_prompt_version: int = 4
    llm_usage_judge_prompt_version: int = 1
    llm_drill_gen_prompt_version: int = 2
    llm_drill_grade_prompt_version: int = 1
    llm_group_gen_prompt_version: int = 1

    editor_max_suggestions: int = 3
    # Empty means nobody is admin until set; /admin/lexicon returns 404.
    admin_user_id: str = ""

    # Per-user LLM ceilings over a rolling 24h window (0 disables that ceiling).
    llm_rate_limit_per_day: int = 200
    llm_cost_limit_usd_per_day: float = 5.0

    # Shown on /about/privacy so users know where messages go.
    llm_privacy_note: str = (
        "User messages are sent to the LLM providers configured for each role "
        "(see LLM_*_MODEL in settings). Hosted providers process text under their "
        "own terms. Ollama keeps traffic on the machine that runs it."
    )


@lru_cache
def get_settings() -> Settings:
    """Cache settings so the environment is parsed once per process."""
    return Settings()
