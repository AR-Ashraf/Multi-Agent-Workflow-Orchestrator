"""Runtime settings (env-driven). No provider/API keys live here — the visitor's
key arrives per-request and is never stored (CLAUDE.md §6 BYOK, §10)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CADENZA_", env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    run_ttl_seconds: int = 1800
    cors_origins: list[str] = ["http://localhost:3000", "https://agents.devs-core.com"]


def get_settings() -> Settings:
    return Settings()
