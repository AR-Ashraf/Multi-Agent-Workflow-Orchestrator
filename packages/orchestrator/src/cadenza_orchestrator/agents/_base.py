"""Shared helpers for agent nodes.

Each agent runs one of two ways, decided by `is_real(ctx)`:
  * **mock** (no key / demo / CI) — deterministic fallback content, byte-identical
    to the fixture graph so the whole suite stays green without live calls.
  * **real** (BYOK key present) — the agent prompts the model and parses its
    structured output, falling back to the deterministic content if the model
    misbehaves. The two paths share one event-emitting body.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

if TYPE_CHECKING:
    from ..context import RunContext


def ctx_from(config: RunnableConfig) -> RunContext:
    """Pull the per-run RunContext threaded through the LangGraph config."""
    return config["configurable"]["ctx"]  # type: ignore[index,typeddict-item]


def is_real(ctx: RunContext) -> bool:
    """True when a real provider client is wired (BYOK run), False for the mock."""
    return getattr(ctx.llm, "provider", "mock") != "mock"


def truncate(text: str, limit: int = 6000) -> str:
    """Cap untrusted/source text fed into a prompt (cost + injection surface)."""
    text = text or ""
    return text if len(text) <= limit else text[:limit] + " …[truncated]"
