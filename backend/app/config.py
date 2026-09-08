from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """All LLM access stays server-side and is controlled by environment values."""

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    mock_mode: bool = True
    openai_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    openai_api_key: str | None = None
    model_name: str = "qwen3.8-flash"
    public_frontend_urls: str = "http://localhost:3000"
    public_backend_url: str = "http://localhost:8000"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    llm_timeout_seconds: float = 20.0

    @property
    def cors_origins(self) -> list[str]:
        """Return the explicit, normalized browser origins allowed to call the API."""
        return [origin.strip().rstrip("/") for origin in self.public_frontend_urls.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
