"""Application configuration."""
from pathlib import Path

from pydantic_settings import BaseSettings
from functools import lru_cache

# Load .env: backend first, then project root (root overrides so your .env wins)
_BACKEND_DIR = Path(__file__).resolve().parent.parent   # backend/
_PROJECT_ROOT = _BACKEND_DIR.parent                      # trend-forecasting-agent/
_ENV_FILES = [p for p in [_BACKEND_DIR / ".env", _PROJECT_ROOT / ".env"] if p.exists()]


class Settings(BaseSettings):
    """App settings from environment."""

    app_name: str = "Trend Forecasting Agent Network"
    debug: bool = False

    # Database
    # Required. Set in .env as DATABASE_URL / DATABASE_URL_SYNC
    database_url: str
    database_url_sync: str

    # Reddit (PRAW)
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "TrendForecastingAgent/1.0"

    # GitHub (optional — higher rate limit with token)
    github_token: str = ""

    # Product Hunt API v2 (Developer token)
    producthunt_api_token: str = ""

    # Google Gemini for Synthesis agent
    google_api_key: str
    gemini_model: str

    # Anonymous comments
    # Used to derive stable anonymous IDs from IP. Set this in .env for production.
    comment_id_salt: str = ""

    # Embedding model
    embedding_model_name: str = "all-MiniLM-L6-v2"

    # Pipeline
    pipeline_top_k_synthesis: int = 10
    pipeline_batch_size_embed: int = 64
    # Synthesis (Gemini): retries, validation, temperature
    synthesis_max_retries: int = 3
    synthesis_temperature: float = 0.2

    # Optional Databricks scheduler mode (backend triggers remote Databricks job every 24h)
    use_databricks_jobs: bool = False
    databricks_host: str = ""
    databricks_token: str = ""
    databricks_pipeline_job_id: int | None = None

    class Config:
        env_file = [str(p) for p in _ENV_FILES] if _ENV_FILES else ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
