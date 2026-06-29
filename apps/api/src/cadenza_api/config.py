"""Runtime settings (env-driven). No provider/API keys live here — the visitor's
key arrives per-request and is never stored (CLAUDE.md §6 BYOK, §10)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CADENZA_", env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    run_ttl_seconds: int = 1800
    cors_origins: list[str] = ["http://localhost:3000", "https://agents.devs-core.com"]

    # --- cost & safety guardrails (CLAUDE.md §8) --------------------------
    # Per-IP rate limit (§8.2): at most N backend runs per window per IP; over
    # the limit the visitor is served the free cached replay. 0 disables it.
    rate_limit_max_runs: int = 5
    rate_limit_window_seconds: int = 60

    # Daily global spend cap (§8.1) — only gates HOUSE-funded runs. With BYOK
    # only (house_api_key unset, the default) the floor stays at $0 and nothing
    # is billed to us; this cap is the safety belt for enabling a house key.
    daily_spend_cap_usd: float = 5.0
    house_api_key: str | None = None
    # Conservative up-front reservation for a house run; settled to actual on
    # completion. Keeps the cap honest under concurrency.
    estimated_run_cost_usd: float = 0.30

    # Per-run ceilings (§8.3), fed into the orchestrator's RunContext. Enforced
    # even on BYOK runs so a runaway loop can't burn the visitor's tokens.
    per_run_max_tokens: int = 250_000
    per_run_max_steps: int = 24


def get_settings() -> Settings:
    return Settings()
