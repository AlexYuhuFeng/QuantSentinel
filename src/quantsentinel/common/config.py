"""
Configuration management (single source of truth).

- Uses pydantic-settings for strong typing & validation
- Reads from environment (.env supported via docker-compose env_file)
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # -----------------------------
    # App
    # -----------------------------
    app_name: str = "QuantSentinel"
    default_language: str = "en"

    # Bootstrap admin (env-overridable; safe dev defaults)
    default_admin_username: str = Field("admin", alias="DEFAULT_ADMIN_USERNAME")
    default_admin_email: str = Field("admin@example.com", alias="DEFAULT_ADMIN_EMAIL")
    default_admin_password: str = Field("Admin@123456", alias="DEFAULT_ADMIN_PASSWORD")
    default_admin_language: str = Field("zh_CN", alias="DEFAULT_ADMIN_LANGUAGE")

    # -----------------------------
    # Database
    # -----------------------------
    database_url: str = Field(
        ...,
        alias="DATABASE_URL",
        description="SQLAlchemy DB URL, e.g. postgresql+psycopg://user:pass@db:5432/quantsentinel",
    )

    db_pool_size: int = Field(5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(10, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(30, alias="DB_POOL_TIMEOUT")

    # -----------------------------
    # Redis / Celery
    # -----------------------------
    redis_url: str = Field("redis://redis:6379/0", alias="REDIS_URL")

    celery_broker_url: str = Field("redis://redis:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://redis:6379/2", alias="CELERY_RESULT_BACKEND")

    # -----------------------------
    # Email (optional)
    # -----------------------------
    email_smtp_host: str | None = Field(None, alias="EMAIL_SMTP_HOST")
    email_smtp_port: int = Field(587, alias="EMAIL_SMTP_PORT")
    email_smtp_user: str | None = Field(None, alias="EMAIL_SMTP_USER")
    email_smtp_password: str | None = Field(None, alias="EMAIL_SMTP_PASSWORD")
    email_from: str | None = Field(None, alias="EMAIL_FROM")

    # -----------------------------
    # Feishu (optional)
    # -----------------------------
    feishu_app_id: str | None = Field(None, alias="FEISHU_APP_ID")
    feishu_app_secret: str | None = Field(None, alias="FEISHU_APP_SECRET")

    # -----------------------------
    # WeChat Work / 企业微信 (optional)
    # -----------------------------
    wechat_corp_id: str | None = Field(None, alias="WECHAT_CORP_ID")
    wechat_corp_secret: str | None = Field(None, alias="WECHAT_CORP_SECRET")
    wechat_agent_id: str | None = Field(None, alias="WECHAT_AGENT_ID")

    # -----------------------------
    # Security
    # -----------------------------
    # For future: JWT/session signing etc (Team Edition currently uses Streamlit session only)
    secret_key: str | None = Field(None, alias="SECRET_KEY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
