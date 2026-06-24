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
    run_id: str
    status: str
    mode: str  # "live" (visitor's key) | "demo" (cached, nothing billed)


class DecisionRequest(BaseModel):
    decision: Literal["approve", "adjust"]
    note: str | None = None


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    mode: str
