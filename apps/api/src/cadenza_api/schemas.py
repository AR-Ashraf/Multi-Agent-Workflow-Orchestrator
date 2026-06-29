"""Request/response models for the gateway."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StartRunRequest(BaseModel):
    query: str = Field(min_length=1, max_length=400)
    provider: str = "anthropic"
    model: str = "claude-sonnet"
    routing: bool = True
    # BYOK: the visitor's provider key. Used per-run only; never stored or logged.
    api_key: str | None = None


class StartRunResponse(BaseModel):
    # `run_id` is null when the gateway gracefully declines a backend run and the
    # client should replay the free cached example instead (CLAUDE.md §8.1/§8.6).
    run_id: str | None = None
    status: str
    mode: str  # "live" (real backend run) | "demo" (cached, nothing billed)
    # Why a demo fallback happened: "no_key" | "rate_limited" | "daily_cap".
    reason: str | None = None


class DecisionRequest(BaseModel):
    decision: Literal["approve", "adjust"]
    note: str | None = None


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    mode: str
