"""
Application configuration (single source of truth).

- Uses pydantic-settings for type-safe environment parsing
- Supports .env loading (via pydantic)
- Centralizes all config access (no direct os.getenv elsewhere)
- Safe repr (does not expose secrets)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Global application settings.

    Loaded from environment variables and optional .env file.
    """

    # -----------------------------
    # Core environment
    # -----------------------------
    environment: Literal["dev", "test", "prod"] = Field(
        default="dev", description="Application environment"
    )

    # -----------------------------
    # Database
    # -----------------------------
    database_url: str = Field(..., description="SQLAlchemy database URL")

    # -----------------------------
    # Redis / Celery
    # -----------------------------
    redis_url: str = Field(..., description="Redis connection URL")
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # -----------------------------
    # Security
    # -----------------------------
    app_secret_key: SecretStr = Field(..., description="Application secret key")

    # -----------------------------
    # Localization
    # -----------------------------
    default_language: str = Field(default="en", description="Default UI language")

    # -----------------------------
    # Server
    # -----------------------------
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8501)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def model_post_init(self, __context):
        """
        Post-processing logic after settings load.
        """
        # If celery URLs not explicitly set, default to redis_url
        if self.celery_broker_url is None:
            self.celery_broker_url = self.redis_url

        if self.celery_result_backend is None:
            self.celery_result_backend = self.redis_url

    def __repr__(self) -> str:
        return (
            "Settings("
            f"environment={self.environment}, "
            f"database_url='***', "
            f"redis_url='{self.redis_url}', "
            f"default_language='{self.default_language}'"
            ")"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached settings loader (singleton per process).

    Ensures all modules share the same config instance.
    """
    return Settings()