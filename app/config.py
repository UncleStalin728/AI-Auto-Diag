from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "service_manuals"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
