"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with defaults suitable for local development."""

    # Database
    database_url: str = "sqlite+aiosqlite:///./tradinghelper.db"

    # Telegram & Ntfy notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    ntfy_topic: str = ""

    # Scanner intervals (seconds)
    scan_interval_intraday_seconds: int = 120
    scan_interval_longterm_seconds: int = 900

    # Alert cooldowns
    alert_cooldown_intraday_minutes: int = 30
    alert_cooldown_longterm_hours: int = 24

    # Market hours (IST) — used by the scanner to skip off-hours
    market_open_hour: int = 9
    market_open_minute: int = 15
    market_close_hour: int = 15
    market_close_minute: int = 30

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Google OAuth & JWT auth
    google_client_id: str = ""
    jwt_secret: str = "change-me-in-production-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()

