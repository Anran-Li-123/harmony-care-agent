from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All LLM access stays server-side and is controlled by environment values."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mock_mode: bool = True
    openai_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    openai_api_key: str | None = None
    model_name: str = "qwen3.8-flash"
    frontend_url: str = "http://localhost:3000"
    llm_timeout_seconds: float = 20.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

